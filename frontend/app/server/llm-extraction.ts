/** Server-only adapter: never import this module from browser code. */
export type SkillEvidence = { skill: string; evidence: string; confidence: "high" | "medium" | "low" };
export type ResumeExtraction = { skills: SkillEvidence[]; experienceSignals: string[]; educationSignals: string[]; unansweredJobCriteria: string[]; reviewWarnings: string[] };

const schema = {
  name: "resume_job_relevant_extraction",
  strict: true,
  schema: {
    type: "object",
    properties: {
      skills: { type: "array", items: { type: "object", properties: { skill: { type: "string" }, evidence: { type: "string" }, confidence: { type: "string", enum: ["high", "medium", "low"] } }, required: ["skill", "evidence", "confidence"], additionalProperties: false } },
      experienceSignals: { type: "array", items: { type: "string" } },
      educationSignals: { type: "array", items: { type: "string" } },
      unansweredJobCriteria: { type: "array", items: { type: "string" } },
      reviewWarnings: { type: "array", items: { type: "string" } },
    },
    required: ["skills", "experienceSignals", "educationSignals", "unansweredJobCriteria", "reviewWarnings"],
    additionalProperties: false,
  },
};

export async function extractJobRelevantResumeFacts(input: { resumeText: string; jobCriteria: string[] }): Promise<ResumeExtraction> {
  if (!process.env.BUILT_IN_FORGE_API_URL || !process.env.BUILT_IN_FORGE_API_KEY) throw new Error("LLM service is not configured");
  const response = await fetch(`${process.env.BUILT_IN_FORGE_API_URL}/v1/chat/completions`, {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.BUILT_IN_FORGE_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      messages: [
        { role: "system", content: "Extract only job-relevant facts explicitly supported by the resume. Do not infer or return age, gender, nationality, religion, disability, health, family status, ethnicity, personality, protected traits, salary expectation, employability, rank, recommendation, or hiring decision. Quote concise evidence. Mark ambiguity for human review." },
        { role: "user", content: `Job criteria:\n${input.jobCriteria.join("\n")}\n\nResume text:\n${input.resumeText}` },
      ],
      response_format: { type: "json_schema", json_schema: schema },
    }),
  });
  if (!response.ok) throw new Error(`LLM extraction failed with ${response.status}`);
  const payload = await response.json() as { choices?: Array<{ message?: { content?: string } }> };
  const text = payload.choices?.[0]?.message?.content;
  if (!text) throw new Error("LLM returned no extraction content");
  return JSON.parse(text) as ResumeExtraction;
}
