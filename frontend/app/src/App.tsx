import {
  type ChangeEvent,
  type CSSProperties,
  type DragEvent,
  useMemo,
  useRef,
  useState,
} from "react";
import { cn } from "./utils/cn";

type Criterion = {
  id: string;
  title: string;
  keywords: string;
  weight: number;
  required: boolean;
};

type CriterionScore = {
  criterionId: string;
  title: string;
  score: number;
  weight: number;
  required: boolean;
  matchedKeywords: string[];
  missingKeywords: string[];
};

type CandidateStatus = "recommended" | "review" | "excluded";
type ResultFilter = "all" | CandidateStatus;

type CandidateResult = {
  id: string;
  fileName: string;
  fileType: string;
  fileSize: number;
  score: number;
  status: CandidateStatus;
  matchedCriteria: number;
  missingRequired: string[];
  criteriaBreakdown: CriterionScore[];
  preview: string;
  email: string;
  phone: string;
  warnings: string[];
  analyzedAt: string;
};

type AnalyzerState = {
  running: boolean;
  progress: number;
  message: string;
};

type MammothLike = {
  extractRawText: (input: { arrayBuffer: ArrayBuffer }) => Promise<{ value: string }>;
};

const defaultCriteria: Criterion[] = [
  {
    id: "criterion-1",
    title: "خبرة React وواجهات حديثة",
    keywords: "React, TypeScript, Vite, Tailwind, frontend, UI",
    weight: 30,
    required: true,
  },
  {
    id: "criterion-2",
    title: "خبرة عملية لا تقل عن 3 سنوات",
    keywords: "3 years, 4 years, 5 years, senior, lead, خبرة, سنوات",
    weight: 25,
    required: true,
  },
  {
    id: "criterion-3",
    title: "تكاملات API والعمل مع البيانات",
    keywords: "REST, GraphQL, API, integrations, database, SQL, Firebase",
    weight: 20,
    required: false,
  },
  {
    id: "criterion-4",
    title: "التواصل والقيادة",
    keywords: "communication, leadership, agile, scrum, mentor, team, قيادة",
    weight: 15,
    required: false,
  },
  {
    id: "criterion-5",
    title: "لغة إنجليزية أو عربية ممتازة",
    keywords: "English, Arabic, bilingual, fluent, عربي, انجليزي, إنجليزي",
    weight: 10,
    required: false,
  },
];

const statusMeta: Record<
  CandidateStatus,
  { label: string; className: string; bar: string }
> = {
  recommended: {
    label: "مرشح قوي",
    className: "bg-emerald-400/12 text-emerald-100 ring-emerald-300/25",
    bar: "bg-emerald-300",
  },
  review: {
    label: "يحتاج مراجعة",
    className: "bg-amber-400/12 text-amber-100 ring-amber-300/25",
    bar: "bg-amber-300",
  },
  excluded: {
    label: "مراجعة إلزامية",
    className: "bg-rose-400/12 text-rose-100 ring-rose-300/25",
    bar: "bg-rose-300",
  },
};

const resultFilters: { value: ResultFilter; label: string }[] = [
  { value: "all", label: "كل النتائج" },
  { value: "recommended", label: "مرشحون أقوياء" },
  { value: "review", label: "للمراجعة" },
  { value: "excluded", label: "مراجعة إلزامية" },
];

const supportedExtensions = ["pdf", "docx", "txt", "md", "rtf", "csv"];
const MAX_BATCH_FILES = 500;
const numberFormatter = new Intl.NumberFormat("ar-EG");
const percentFormatter = new Intl.NumberFormat("ar-EG", {
  maximumFractionDigits: 0,
});

export default function App() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [criteria, setCriteria] = useState<Criterion[]>(defaultCriteria);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [results, setResults] = useState<CandidateResult[]>([]);
  const [analysis, setAnalysis] = useState<AnalyzerState>({
    running: false,
    progress: 0,
    message: "جاهز لاستقبال الملفات",
  });
  const [minimumScore, setMinimumScore] = useState(72);
  const [shortlistSize, setShortlistSize] = useState(25);
  const [resultFilter, setResultFilter] = useState<ResultFilter>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [dragActive, setDragActive] = useState(false);

  const totalWeight = useMemo(
    () => criteria.reduce((total, criterion) => total + criterion.weight, 0),
    [criteria],
  );

  const orderedResults = useMemo(() => [...results].sort(sortCandidates), [results]);

  const filteredResults = useMemo(() => {
    const normalizedSearch = normalizeText(searchTerm);

    return orderedResults.filter((result) => {
      const matchesStatus =
        resultFilter === "all" ? true : result.status === resultFilter;
      const matchesSearch = normalizedSearch
        ? normalizeText(`${result.fileName} ${result.email} ${result.phone}`).includes(
            normalizedSearch,
          )
        : true;

      return matchesStatus && matchesSearch;
    });
  }, [orderedResults, resultFilter, searchTerm]);

  const shortlist = useMemo(
    () =>
      orderedResults
        .filter((result) => result.status === "recommended")
        .slice(0, shortlistSize),
    [orderedResults, shortlistSize],
  );

  const bestCandidate = shortlist[0] ?? orderedResults[0] ?? null;
  const recommendedCount = results.filter(
    (result) => result.status === "recommended",
  ).length;
  const reviewCount = results.filter((result) => result.status === "review").length;
  const excludedCount = results.filter((result) => result.status === "excluded").length;
  const averageScore = results.length
    ? Math.round(
        results.reduce((total, result) => total + result.score, 0) / results.length,
      )
    : 0;
  const skillCoverage = useMemo(
    () =>
      criteria.map((criterion) => {
        const matched = results.filter((result) =>
          result.criteriaBreakdown.some(
            (item) => item.criterionId === criterion.id && item.score > 0,
          ),
        ).length;
        return { ...criterion, matched, percent: results.length ? Math.round((matched / results.length) * 100) : 0 };
      }),
    [criteria, results],
  );
  const extractionComplete = results.filter((result) => !result.warnings.length).length;
  const uploadedSize = selectedFiles.reduce((total, file) => total + file.size, 0);
  const canAnalyze = selectedFiles.length > 0 && criteria.length > 0 && !analysis.running;

  function handleFileInput(event: ChangeEvent<HTMLInputElement>) {
    addFiles(event.target.files);
    event.target.value = "";
  }

  function addFiles(fileList: FileList | File[] | null) {
    if (!fileList) {
      return;
    }

    const incomingFiles = Array.from(fileList).filter(isSupportedFile);

    if (!incomingFiles.length) {
      setAnalysis({
        running: false,
        progress: 0,
        message: "لم يتم العثور على ملفات مدعومة. استخدم PDF أو DOCX أو TXT.",
      });
      return;
    }

    const availableSlots = Math.max(0, MAX_BATCH_FILES - selectedFiles.length);
    const acceptedFiles = incomingFiles.slice(0, availableSlots);
    if (!acceptedFiles.length) {
      setAnalysis({ running: false, progress: 0, message: "وصلت الدفعة إلى الحد الأقصى البالغ 500 سيرة." });
      return;
    }
    setSelectedFiles((currentFiles) => {
      const knownFiles = new Set(currentFiles.map(getFileKey));
      const mergedFiles = [...currentFiles];

      acceptedFiles.forEach((file) => {
        const key = getFileKey(file);
        if (!knownFiles.has(key)) {
          knownFiles.add(key);
          mergedFiles.push(file);
        }
      });

      return mergedFiles;
    });
    setResults([]);
    setAnalysis({
      running: false,
      progress: 0,
      message: incomingFiles.length > acceptedFiles.length
        ? `تم تجهيز ${formatNumber(acceptedFiles.length)} ملف؛ تم تأجيل الملفات الزائدة لأن الحد هو 500 سيرة.`
        : `تم تجهيز ${formatNumber(acceptedFiles.length)} ملف للتحليل`,
    });
  }

  function removeFile(fileKey: string) {
    setSelectedFiles((currentFiles) =>
      currentFiles.filter((file) => getFileKey(file) !== fileKey),
    );
    setResults([]);
  }

  function clearFiles() {
    setSelectedFiles([]);
    setResults([]);
    setAnalysis({ running: false, progress: 0, message: "تم تفريغ قائمة الملفات" });
  }

  function updateCriterion(
    criterionId: string,
    patch: Partial<Omit<Criterion, "id">>,
  ) {
    setCriteria((currentCriteria) =>
      currentCriteria.map((criterion) =>
        criterion.id === criterionId ? { ...criterion, ...patch } : criterion,
      ),
    );
    setResults([]);
  }

  function addCriterion() {
    setCriteria((currentCriteria) => [
      ...currentCriteria,
      {
        id: createId("criterion"),
        title: "معيار جديد",
        keywords: "keyword 1, keyword 2",
        weight: 10,
        required: false,
      },
    ]);
    setResults([]);
  }

  function removeCriterion(criterionId: string) {
    setCriteria((currentCriteria) =>
      currentCriteria.filter((criterion) => criterion.id !== criterionId),
    );
    setResults([]);
  }

  function resetCriteria() {
    setCriteria(defaultCriteria);
    setResults([]);
  }

  function handleDrag(event: DragEvent<HTMLDivElement>, active: boolean) {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(active);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    handleDrag(event, false);
    addFiles(event.dataTransfer.files);
  }

  async function analyzeFiles() {
    if (!canAnalyze) {
      return;
    }

    setResults([]);
    setAnalysis({ running: true, progress: 0, message: "بدء قراءة السير الذاتية" });

    const completedResults: CandidateResult[] = [];
    let completed = 0;
    const concurrency = 5;

    for (let index = 0; index < selectedFiles.length; index += concurrency) {
      const batch = selectedFiles.slice(index, index + concurrency);
      const batchResults = await Promise.all(
        batch.map(async (file) => {
          const result = await analyzeFile(file, criteria, minimumScore);
          completed += 1;
          setAnalysis({
            running: true,
            progress: Math.round((completed / selectedFiles.length) * 100),
            message: `تم تحليل ${formatNumber(completed)} من ${formatNumber(
              selectedFiles.length,
            )}`,
          });
          return result;
        }),
      );

      completedResults.push(...batchResults);
      setResults([...completedResults].sort(sortCandidates));
    }

    setAnalysis({
      running: false,
      progress: 100,
      message: `اكتمل التحليل. تم اختيار ${formatNumber(
        completedResults.filter((result) => result.status === "recommended").length,
      )} مرشح قوي`,
    });
  }

  function exportCsv() {
    if (!orderedResults.length) {
      return;
    }

    const header = [
      "rank",
      "file_name",
      "score",
      "status",
      "matched_criteria",
      "missing_required",
      "email",
      "phone",
      "warnings",
    ];
    const rows = orderedResults.map((result, index) => [
      String(index + 1),
      result.fileName,
      String(result.score),
      statusMeta[result.status].label,
      String(result.matchedCriteria),
      result.missingRequired.join(" | "),
      result.email,
      result.phone,
      result.warnings.join(" | "),
    ]);
    const csv = [header, ...rows].map(toCsvRow).join("\n");
    const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "MY-CV-shortlist.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main
      dir="rtl"
      className="min-h-screen overflow-hidden bg-[#07111f] text-white"
    >
      <div className="relative isolate min-h-screen">
        <div className="cv-orb cv-orb-one" />
        <div className="cv-orb cv-orb-two" />
        <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-5 py-5 sm:px-8 lg:px-10">
          <header className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="grid h-12 w-12 place-items-center rounded-2xl bg-cyan-300 text-lg font-black text-slate-950 shadow-xl shadow-cyan-500/20">
                CV
              </div>
              <div>
                <p className="text-2xl font-black tracking-tight">MY-CV</p>
                <p className="mt-1 text-xs font-semibold text-slate-400">
                  منصة فرز السير الذاتية حسب معايير الشركة
                </p>
              </div>
            </div>

            <div className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-xs font-bold text-slate-300 backdrop-blur sm:flex">
              <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_18px_rgba(110,231,183,0.8)]" />
              معالجة محلية داخل المتصفح
            </div>
          </header>

          <section className="grid flex-1 gap-8 py-8 lg:grid-cols-[minmax(0,1fr)_390px] xl:grid-cols-[minmax(0,1fr)_430px]">
            <div className="min-w-0 space-y-6">
              <div className="max-w-4xl">
                <p className="text-sm font-black text-cyan-200">
                  ارفع أكثر من 500 سيرة ذاتية ودع النظام يرتب الأفضل
                </p>
                <h1 className="mt-4 text-6xl font-black leading-[0.9] tracking-tight sm:text-7xl lg:text-8xl">
                  MY-CV
                  <span className="mt-4 block text-3xl leading-tight text-slate-300 sm:text-4xl lg:text-5xl">
                    يختار المرشحين الأقرب لمعايير شركتك.
                  </span>
                </h1>
                <p className="mt-5 max-w-3xl text-base leading-8 text-slate-300 sm:text-lg">
                  حدد المهارات المطلوبة، الأوزان، والشروط الإلزامية. بعد رفع ملفات
                  PDF أو DOCX أو TXT يقوم MY-CV بقراءة النصوص، حساب درجة كل مرشح،
                  واستبعاد من لا يطابق الشروط الأساسية.
                </p>
              </div>

              <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
                <div
                  onDragEnter={(event) => handleDrag(event, true)}
                  onDragOver={(event) => handleDrag(event, true)}
                  onDragLeave={(event) => handleDrag(event, false)}
                  onDrop={handleDrop}
                  className={cn(
                    "upload-zone group relative overflow-hidden rounded-[2rem] border border-dashed p-5 transition",
                    dragActive
                      ? "border-cyan-200 bg-cyan-300/10"
                      : "border-white/15 bg-white/[0.055] hover:border-cyan-200/70 hover:bg-white/[0.075]",
                  )}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".pdf,.docx,.txt,.md,.rtf,.csv"
                    onChange={handleFileInput}
                    className="hidden"
                  />
                  <div className="relative space-y-5">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-2xl font-black">رفع السير الذاتية</p>
                        <p className="mt-2 text-sm leading-6 text-slate-400">
                          اسحب الملفات هنا أو اخترها دفعة واحدة. الواجهة مصممة
                          لمعالجة أكثر من 500 ملف على دفعات.
                        </p>
                      </div>
                      <div className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-cyan-300 text-xl font-black text-slate-950">
                        +500
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="w-full rounded-2xl bg-cyan-300 px-5 py-4 text-base font-black text-slate-950 transition hover:-translate-y-0.5 hover:bg-cyan-200 focus:outline-none focus:ring-2 focus:ring-cyan-100"
                    >
                      اختيار ملفات CV
                    </button>

                    <div className="grid grid-cols-3 gap-2 text-center text-xs font-bold text-slate-400">
                      <span className="rounded-2xl bg-white/[0.06] px-3 py-2">PDF</span>
                      <span className="rounded-2xl bg-white/[0.06] px-3 py-2">DOCX</span>
                      <span className="rounded-2xl bg-white/[0.06] px-3 py-2">TXT</span>
                    </div>

                    <div className="rounded-2xl bg-slate-950/40 p-4">
                      <div className="flex items-center justify-between gap-3 text-sm">
                        <span className="font-bold text-slate-300">الملفات المختارة</span>
                        <span className="font-black text-white">
                          {formatNumber(selectedFiles.length)}
                        </span>
                      </div>
                      <div className="mt-3 flex items-center justify-between gap-3 text-xs text-slate-500">
                        <span>{formatFileSize(uploadedSize)}</span>
                        <button
                          type="button"
                          onClick={clearFiles}
                          disabled={!selectedFiles.length || analysis.running}
                          className="font-bold text-slate-400 transition hover:text-rose-200 disabled:pointer-events-none disabled:opacity-40"
                        >
                          تفريغ القائمة
                        </button>
                      </div>
                    </div>

                    {selectedFiles.length ? (
                      <div className="max-h-40 space-y-2 overflow-auto pr-1">
                        {selectedFiles.slice(0, 10).map((file) => (
                          <div
                            key={getFileKey(file)}
                            className="flex items-center justify-between gap-3 rounded-2xl bg-white/[0.05] px-3 py-2 text-xs"
                          >
                            <span className="min-w-0 truncate font-bold text-slate-200">
                              {file.name}
                            </span>
                            <button
                              type="button"
                              onClick={() => removeFile(getFileKey(file))}
                              disabled={analysis.running}
                              className="shrink-0 text-slate-500 transition hover:text-rose-200 disabled:pointer-events-none"
                            >
                              حذف
                            </button>
                          </div>
                        ))}
                        {selectedFiles.length > 10 ? (
                          <p className="text-center text-xs font-bold text-slate-500">
                            و {formatNumber(selectedFiles.length - 10)} ملف آخر
                          </p>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                </div>

                <div className="rounded-[2rem] border border-white/10 bg-white/[0.055] p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-2xl font-black">إعدادات الاختيار</p>
                      <p className="mt-2 text-sm leading-6 text-slate-400">
                        اضبط الحد الأدنى وعدد المرشحين في القائمة القصيرة.
                      </p>
                    </div>
                    <button
                      type="button"
                      disabled
                      className="rounded-full border border-white/10 px-4 py-2 text-xs font-black text-slate-500"
                    >
                      بلا بيانات تجريبية
                    </button>
                  </div>

                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    <label className="rounded-2xl bg-slate-950/35 p-4 text-sm font-bold text-slate-300">
                      حد القبول
                      <input
                        type="range"
                        min="40"
                        max="95"
                        value={minimumScore}
                        onChange={(event) => setMinimumScore(Number(event.target.value))}
                        className="mt-4 w-full accent-cyan-300"
                      />
                      <span className="mt-2 block text-2xl font-black text-white">
                        {formatPercent(minimumScore)}%
                      </span>
                    </label>

                    <label className="rounded-2xl bg-slate-950/35 p-4 text-sm font-bold text-slate-300">
                      القائمة القصيرة
                      <input
                        type="number"
                        min="1"
                        max="250"
                        value={shortlistSize}
                        onChange={(event) =>
                          setShortlistSize(Math.max(1, Number(event.target.value)))
                        }
                        className="mt-4 w-full rounded-xl border border-white/10 bg-white/[0.06] px-3 py-2 text-lg font-black text-white outline-none focus:border-cyan-200/70"
                      />
                      <span className="mt-2 block text-xs text-slate-500">
                        أعلى المرشحين الذين تجاوزوا الحد
                      </span>
                    </label>
                  </div>

                  <div className="mt-5 rounded-2xl bg-slate-950/35 p-4">
                    <div className="flex items-center justify-between gap-3 text-sm">
                      <span className="font-bold text-slate-300">حالة التحليل</span>
                      <span className="font-black text-cyan-100">
                        {formatPercent(analysis.progress)}%
                      </span>
                    </div>
                    <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10">
                      <div
                        className="progress-fill h-full rounded-full bg-cyan-300"
                        style={{ width: `${analysis.progress}%` }}
                      />
                    </div>
                    <p className="mt-3 text-xs font-semibold text-slate-400">
                      {analysis.message}
                    </p>
                  </div>

                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    <button
                      type="button"
                      onClick={analyzeFiles}
                      disabled={!canAnalyze}
                      className="rounded-2xl bg-white px-5 py-4 text-base font-black text-slate-950 transition hover:-translate-y-0.5 hover:bg-cyan-100 focus:outline-none focus:ring-2 focus:ring-cyan-100 disabled:pointer-events-none disabled:opacity-40"
                    >
                      {analysis.running ? "جار التحليل" : "تحليل السير"}
                    </button>
                    <button
                      type="button"
                      onClick={exportCsv}
                      disabled={!orderedResults.length || analysis.running}
                      className="rounded-2xl border border-white/10 px-5 py-4 text-base font-black text-white transition hover:-translate-y-0.5 hover:border-cyan-200/60 hover:text-cyan-100 disabled:pointer-events-none disabled:opacity-40"
                    >
                      تصدير CSV
                    </button>
                  </div>
                </div>
              </section>

              <section className="rounded-[2rem] border border-white/10 bg-white/[0.055] p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-2xl font-black">معايير الشركة</p>
                    <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
                      اكتب الكلمات المفتاحية لكل معيار وافصل بينها بفواصل. الوزن
                      يحدد تأثير المعيار، والشرط الإلزامي يستبعد المرشح إذا لم يتحقق.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={addCriterion}
                      className="rounded-full bg-cyan-300 px-4 py-2 text-xs font-black text-slate-950 transition hover:-translate-y-0.5 hover:bg-cyan-200"
                    >
                      إضافة معيار
                    </button>
                    <button
                      type="button"
                      onClick={resetCriteria}
                      className="rounded-full border border-white/10 px-4 py-2 text-xs font-black text-slate-300 transition hover:-translate-y-0.5 hover:border-white/25 hover:text-white"
                    >
                      استعادة الافتراضي
                    </button>
                  </div>
                </div>

                <div className="mt-5 space-y-3">
                  {criteria.map((criterion, index) => (
                    <div
                      key={criterion.id}
                      className="criteria-row grid gap-3 rounded-2xl bg-slate-950/35 p-3 lg:grid-cols-[1fr_1.25fr_120px_120px_auto]"
                      style={{ animationDelay: `${index * 35}ms` }}
                    >
                      <label className="text-xs font-bold text-slate-400">
                        اسم المعيار
                        <input
                          value={criterion.title}
                          onChange={(event) =>
                            updateCriterion(criterion.id, { title: event.target.value })
                          }
                          className="mt-2 w-full rounded-xl border border-white/10 bg-white/[0.06] px-3 py-2 text-sm font-bold text-white outline-none focus:border-cyan-200/70"
                        />
                      </label>

                      <label className="text-xs font-bold text-slate-400">
                        الكلمات المفتاحية
                        <input
                          value={criterion.keywords}
                          onChange={(event) =>
                            updateCriterion(criterion.id, {
                              keywords: event.target.value,
                            })
                          }
                          className="mt-2 w-full rounded-xl border border-white/10 bg-white/[0.06] px-3 py-2 text-sm font-bold text-white outline-none focus:border-cyan-200/70"
                        />
                      </label>

                      <label className="text-xs font-bold text-slate-400">
                        الوزن
                        <input
                          type="number"
                          min="1"
                          max="100"
                          value={criterion.weight}
                          onChange={(event) =>
                            updateCriterion(criterion.id, {
                              weight: Math.max(1, Number(event.target.value)),
                            })
                          }
                          className="mt-2 w-full rounded-xl border border-white/10 bg-white/[0.06] px-3 py-2 text-sm font-black text-white outline-none focus:border-cyan-200/70"
                        />
                      </label>

                      <label className="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.04] px-3 py-3 text-xs font-bold text-slate-300 lg:mt-5">
                        إلزامي
                        <input
                          type="checkbox"
                          checked={criterion.required}
                          onChange={(event) =>
                            updateCriterion(criterion.id, {
                              required: event.target.checked,
                            })
                          }
                          className="h-4 w-4 accent-cyan-300"
                        />
                      </label>

                      <button
                        type="button"
                        onClick={() => removeCriterion(criterion.id)}
                        disabled={criteria.length === 1}
                        className="rounded-xl px-3 py-2 text-xs font-black text-slate-500 transition hover:bg-rose-400/10 hover:text-rose-100 disabled:pointer-events-none disabled:opacity-30 lg:mt-5"
                      >
                        حذف
                      </button>
                    </div>
                  ))}
                </div>

                <div className="mt-4 flex flex-wrap items-center gap-3 text-xs font-bold text-slate-400">
                  <span>عدد المعايير: {formatNumber(criteria.length)}</span>
                  <span className="h-1 w-1 rounded-full bg-slate-600" />
                  <span>مجموع الأوزان: {formatNumber(totalWeight)}</span>
                </div>
              </section>
            </div>

            <aside className="relative overflow-hidden rounded-[2.4rem] border border-cyan-200/15 bg-slate-950/78 p-6 shadow-2xl shadow-cyan-950/30 lg:sticky lg:top-6">
              <div className="absolute inset-x-0 top-0 h-48 bg-[radial-gradient(circle_at_top,rgba(103,232,249,0.22),transparent_68%)]" />
              <div className="relative space-y-7">
                <div>
                  <p className="text-sm font-black text-cyan-200">قرار التوظيف المختصر</p>
                  <h2 className="mt-2 text-3xl font-black tracking-tight">
                    أفضل مرشح حاليا
                  </h2>
                  <p className="mt-3 text-sm leading-7 text-slate-400">
                    يتم ترتيب المرشحين حسب الدرجة، الشروط الإلزامية، وعدد المعايير
                    المطابقة. يمكن تصدير القائمة لاستخدامها مع فريق الموارد البشرية.
                  </p>
                </div>

                <div className="grid grid-cols-[132px_1fr] items-center gap-5">
                  <ScoreRing value={bestCandidate?.score ?? 0} />
                  <div className="space-y-4">
                    <Metric label="تم تحليلها" value={formatNumber(results.length)} />
                    <Metric label="مرشحون أقوياء" value={formatNumber(recommendedCount)} />
                    <Metric label="متوسط الدرجات" value={`${formatPercent(averageScore)}%`} />
                  </div>
                </div>

                {bestCandidate ? (
                  <div className="rounded-[1.7rem] border border-white/10 bg-white/[0.055] p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <p className="truncate text-lg font-black">
                          {bestCandidate.fileName}
                        </p>
                        <p className="mt-1 text-xs font-bold text-slate-500">
                          {bestCandidate.fileType}، {formatFileSize(bestCandidate.fileSize)}
                        </p>
                      </div>
                      <StatusBadge status={bestCandidate.status} />
                    </div>
                    <p className="mt-4 line-clamp-4 text-sm leading-7 text-slate-300">
                      {bestCandidate.preview}
                    </p>
                    <div className="mt-4 grid gap-2 text-xs font-bold text-slate-400">
                      <span>البريد: {bestCandidate.email || "غير موجود"}</span>
                      <span>الهاتف: {bestCandidate.phone || "غير موجود"}</span>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-[1.7rem] border border-dashed border-white/15 p-5 text-sm leading-7 text-slate-400">
                    لم يتم تحليل أي سيرة بعد. ارفع ملفات حقيقية بعد الحصول على
                    موافقة الشركة والمرشحين.
                  </div>
                )}

                <div className="grid grid-cols-3 gap-2 text-center">
                  <MiniMetric label="قوي" value={recommendedCount} tone="text-emerald-200" />
                  <MiniMetric label="مراجعة" value={reviewCount} tone="text-amber-200" />
                  <MiniMetric label="مستبعد" value={excludedCount} tone="text-rose-200" />
                </div>

                <div className="border-t border-white/10 pt-6">
                  <h3 className="text-xl font-black">القائمة القصيرة</h3>
                  <div className="mt-4 space-y-2">
                    {shortlist.length ? (
                      shortlist.slice(0, 6).map((result, index) => (
                        <div
                          key={result.id}
                          className="flex items-center justify-between gap-3 rounded-2xl bg-white/[0.055] px-4 py-3"
                        >
                          <span className="min-w-0">
                            <span className="block truncate text-sm font-black text-white">
                              {formatNumber(index + 1)}. {result.fileName}
                            </span>
                            <span className="mt-1 block text-xs font-bold text-slate-500">
                              {formatNumber(result.matchedCriteria)} معايير مطابقة
                            </span>
                          </span>
                          <span className="text-lg font-black text-cyan-100">
                            {formatPercent(result.score)}%
                          </span>
                        </div>
                      ))
                    ) : (
                      <p className="rounded-2xl bg-white/[0.055] px-4 py-5 text-sm leading-7 text-slate-400">
                        ستظهر هنا أفضل النتائج التي تجاوزت حد القبول.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </aside>
          </section>

          <section className="pb-8">
            <div className="rounded-[2.2rem] border border-emerald-200/15 bg-emerald-300/[0.035] p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-2xl font-black">لوحة إشارات المراجعة</p>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
                    تعرض هذه اللوحة دلائل استخراج ومقارنة مرتبطة بالدور الوظيفي. لا تمثل توصية توظيف أو تقييمًا للشخصية.
                  </p>
                </div>
                <span className="rounded-full border border-emerald-200/20 bg-emerald-200/10 px-4 py-2 text-xs font-black text-emerald-100">
                  مراجعة بشرية مطلوبة
                </span>
              </div>
              <div className="mt-5 grid gap-3 sm:grid-cols-3">
                <MiniMetric label="استخراج مكتمل" value={extractionComplete} tone="text-emerald-200" />
                <MiniMetric label="يتطلب تحققًا" value={results.length - extractionComplete} tone="text-amber-200" />
                <MiniMetric label="متوسط المطابقة" value={averageScore} tone="text-cyan-100" />
              </div>
              <div className="mt-5 grid gap-5 lg:grid-cols-[1.15fr_.85fr]">
                <div className="rounded-2xl bg-slate-950/35 p-4">
                  <p className="text-sm font-black text-slate-200">تغطية المعايير في الدفعة</p>
                  <div className="mt-4 space-y-3">
                    {skillCoverage.map((item) => (
                      <div key={item.id}>
                        <div className="flex items-center justify-between gap-3 text-xs font-bold text-slate-400"><span>{item.title}</span><span>{formatPercent(item.percent)}% · {formatNumber(item.matched)}</span></div>
                        <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-emerald-300" style={{ width: `${item.percent}%` }} /></div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="rounded-2xl bg-slate-950/35 p-4">
                  <p className="text-sm font-black text-slate-200">مقارنة مرشحين للمراجع</p>
                  <div className="mt-4 space-y-2">
                    {shortlist.slice(0, 3).length ? shortlist.slice(0, 3).map((result) => (
                      <div key={result.id} className="flex items-center justify-between gap-3 rounded-xl bg-white/[0.04] px-3 py-3"><span className="min-w-0 truncate text-xs font-bold text-slate-300">{result.fileName}</span><span className="shrink-0 text-sm font-black text-cyan-100">{formatPercent(result.score)}%</span></div>
                    )) : <p className="text-sm leading-7 text-slate-500">ستظهر المقارنة بعد تحليل ملفات حقيقية.</p>}
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="pb-10">
            <div className="rounded-[2.2rem] border border-white/10 bg-white/[0.055] p-5">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-2xl font-black">نتائج التحليل</p>
                  <p className="mt-2 text-sm text-slate-400">
                    مرتبة من الأقوى إلى الأقل ملاءمة بناء على معايير الشركة.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {resultFilters.map((filter) => (
                    <button
                      key={filter.value}
                      type="button"
                      onClick={() => setResultFilter(filter.value)}
                      className={cn(
                        "rounded-full px-4 py-2 text-xs font-black transition",
                        resultFilter === filter.value
                          ? "bg-cyan-300 text-slate-950"
                          : "border border-white/10 text-slate-300 hover:border-cyan-200/60 hover:text-cyan-100",
                      )}
                    >
                      {filter.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-[1fr_auto]">
                <input
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  placeholder="بحث باسم الملف أو البريد أو الهاتف"
                  className="rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-sm font-bold text-white outline-none placeholder:text-slate-600 focus:border-cyan-200/70"
                />
                <div className="rounded-2xl bg-slate-950/40 px-4 py-3 text-sm font-black text-slate-300">
                  {formatNumber(filteredResults.length)} نتيجة ظاهرة
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {filteredResults.length ? (
                  filteredResults.map((result, index) => (
                    <ResultRow key={result.id} result={result} rank={index + 1} />
                  ))
                ) : (
                  <div className="rounded-[1.6rem] border border-dashed border-white/15 p-8 text-center text-sm leading-7 text-slate-400">
                    لا توجد نتائج مطابقة حاليا. ارفع ملفات ثم اضغط تحليل السير،
                    وبعدها راجع الأسباب قبل أي قرار بشري.
                  </div>
                )}
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

function ResultRow({ result, rank }: { result: CandidateResult; rank: number }) {
  const topMatches = result.criteriaBreakdown
    .filter((criterion) => criterion.score > 0)
    .sort((first, second) => second.score - first.score)
    .slice(0, 3);

  return (
    <article className="result-row rounded-[1.7rem] border border-white/10 bg-slate-950/38 p-4">
      <div className="grid gap-4 lg:grid-cols-[80px_1fr_170px] lg:items-start">
        <div className="flex items-center gap-3 lg:block">
          <span className="grid h-12 w-12 place-items-center rounded-2xl bg-white text-lg font-black text-slate-950 lg:mx-auto">
            {formatNumber(rank)}
          </span>
          <div className="lg:mt-3 lg:text-center">
            <p className="text-2xl font-black text-cyan-100">
              {formatPercent(result.score)}%
            </p>
            <p className="text-xs font-bold text-slate-500">درجة</p>
          </div>
        </div>

        <div className="min-w-0">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="truncate text-lg font-black text-white">{result.fileName}</h3>
              <p className="mt-1 text-xs font-bold text-slate-500">
                {result.fileType}، {formatFileSize(result.fileSize)}، تم التحليل {result.analyzedAt}
              </p>
            </div>
            <StatusBadge status={result.status} />
          </div>

          <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/10">
            <div
              className={cn("h-full rounded-full", statusMeta[result.status].bar)}
              style={{ width: `${result.score}%` }}
            />
          </div>

          <p className="mt-4 line-clamp-3 text-sm leading-7 text-slate-300">
            {result.preview}
          </p>

          <div className="mt-4 flex flex-wrap gap-2">
            {topMatches.map((criterion) => (
              <span
                key={criterion.criterionId}
                className="rounded-full bg-cyan-300/10 px-3 py-1 text-xs font-bold text-cyan-100 ring-1 ring-cyan-200/15"
              >
                {criterion.title}: {formatPercent(criterion.score)}%
              </span>
            ))}
            {result.missingRequired.map((criterion) => (
              <span
                key={criterion}
                className="rounded-full bg-rose-300/10 px-3 py-1 text-xs font-bold text-rose-100 ring-1 ring-rose-200/15"
              >
                ناقص: {criterion}
              </span>
            ))}
          </div>
        </div>

        <div className="space-y-3 rounded-2xl bg-white/[0.04] p-4 text-xs font-bold text-slate-400">
          <p>البريد: {result.email || "غير موجود"}</p>
          <p>الهاتف: {result.phone || "غير موجود"}</p>
          <p>المعايير المطابقة: {formatNumber(result.matchedCriteria)}</p>
          {result.warnings.length ? (
            <p className="leading-6 text-amber-200">تنبيه: {result.warnings.join("، ")}</p>
          ) : null}
        </div>
      </div>
    </article>
  );
}

function StatusBadge({ status }: { status: CandidateStatus }) {
  return (
    <span
      className={cn(
        "shrink-0 rounded-full px-3 py-1.5 text-xs font-black ring-1",
        statusMeta[status].className,
      )}
    >
      {statusMeta[status].label}
    </span>
  );
}

function ScoreRing({ value }: { value: number }) {
  const radius = 48;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className="relative h-32 w-32">
      <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120" role="img">
        <title>درجة أفضل مرشح</title>
        <circle
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.11)"
          strokeWidth="12"
        />
        <circle
          className="score-ring"
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          stroke="#67e8f9"
          strokeLinecap="round"
          strokeWidth="12"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ "--ring-circumference": circumference } as CSSProperties}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-black text-white">{formatPercent(value)}%</span>
        <span className="text-xs font-bold text-slate-500">مطابقة</span>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-bold text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-black text-white">{value}</p>
    </div>
  );
}

function MiniMetric({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: string;
}) {
  return (
    <div className="rounded-2xl bg-white/[0.055] px-3 py-4">
      <p className={cn("text-2xl font-black", tone)}>{formatNumber(value)}</p>
      <p className="mt-1 text-xs font-bold text-slate-500">{label}</p>
    </div>
  );
}

async function analyzeFile(
  file: File,
  criteria: Criterion[],
  minimumScore: number,
) {
  const extraction = await extractFileText(file);

  return analyzeTextSource({
    fileName: file.name,
    fileType: getFileExtension(file.name).toUpperCase() || file.type || "FILE",
    fileSize: file.size,
    text: `${file.name}\n${extraction.text}`,
    criteria,
    minimumScore,
    warnings: extraction.warnings,
  });
}

function analyzeTextSource({
  fileName,
  fileType,
  fileSize,
  text,
  criteria,
  minimumScore,
  warnings,
}: {
  fileName: string;
  fileType: string;
  fileSize: number;
  text: string;
  criteria: Criterion[];
  minimumScore: number;
  warnings: string[];
}): CandidateResult {
  const normalizedText = normalizeText(text);
  const totalWeight = criteria.reduce((total, criterion) => total + criterion.weight, 0);
  const criteriaBreakdown = criteria.map((criterion) =>
    scoreCriterion(criterion, normalizedText),
  );
  const weightedScore = totalWeight
    ? criteriaBreakdown.reduce(
        (total, criterion) => total + criterion.score * criterion.weight,
        0,
      ) / totalWeight
    : 0;
  const score = Math.round(weightedScore);
  const missingRequired = criteriaBreakdown
    .filter((criterion) => criterion.required && criterion.score === 0)
    .map((criterion) => criterion.title);
  const status: CandidateStatus = missingRequired.length
    ? "review"
    : score >= minimumScore
      ? "recommended"
      : "review";

  return {
    id: createId("candidate"),
    fileName,
    fileType,
    fileSize,
    score,
    status,
    matchedCriteria: criteriaBreakdown.filter((criterion) => criterion.score > 0).length,
    missingRequired,
    criteriaBreakdown,
    preview: createPreview(text),
    email: extractEmail(text),
    phone: extractPhone(text),
    warnings,
    analyzedAt: new Intl.DateTimeFormat("ar-EG", {
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date()),
  };
}

async function extractFileText(file: File): Promise<{ text: string; warnings: string[] }> {
  const extension = getFileExtension(file.name);

  try {
    if (extension === "pdf") {
      return extractPdfText(file);
    }

    if (extension === "docx") {
      return extractDocxText(file);
    }

    if (["txt", "md", "rtf", "csv"].includes(extension)) {
      return { text: await file.text(), warnings: [] };
    }

    return {
      text: file.name,
      warnings: ["نوع الملف غير مدعوم بالكامل وتم الاعتماد على اسم الملف فقط"],
    };
  } catch (error) {
    return {
      text: file.name,
      warnings: [
        `تعذر استخراج النص: ${error instanceof Error ? error.message : "خطأ غير معروف"}`,
      ],
    };
  }
}

async function extractPdfText(file: File): Promise<{ text: string; warnings: string[] }> {
  const pdfjsLib = await import("pdfjs-dist");
  pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
    "pdfjs-dist/build/pdf.worker.min.mjs",
    import.meta.url,
  ).toString();

  const loadingTask = pdfjsLib.getDocument({
    data: new Uint8Array(await file.arrayBuffer()),
  });
  const pdf = await loadingTask.promise;
  const pagesToRead = Math.min(pdf.numPages, 12);
  const pageTexts: string[] = [];

  for (let pageNumber = 1; pageNumber <= pagesToRead; pageNumber += 1) {
    const page = await pdf.getPage(pageNumber);
    const content = await page.getTextContent();
    pageTexts.push(
      content.items.map((item) => (isPdfTextItem(item) ? item.str : "")).join(" "),
    );
  }

  pdf.cleanup();

  return {
    text: pageTexts.join("\n"),
    warnings:
      pdf.numPages > pagesToRead
        ? [`تمت قراءة أول ${formatNumber(pagesToRead)} صفحة فقط لتسريع التحليل`]
        : [],
  };
}

async function extractDocxText(file: File): Promise<{ text: string; warnings: string[] }> {
  const mammothModule = (await import("mammoth")) as unknown as
    | MammothLike
    | { default: MammothLike };
  const mammoth = "default" in mammothModule ? mammothModule.default : mammothModule;
  const result = await mammoth.extractRawText({ arrayBuffer: await file.arrayBuffer() });

  return { text: result.value, warnings: [] };
}

function scoreCriterion(criterion: Criterion, normalizedText: string): CriterionScore {
  const keywords = splitKeywords(criterion.keywords || criterion.title);
  const matchedKeywords = keywords.filter((keyword) =>
    normalizedText.includes(normalizeText(keyword)),
  );
  const missingKeywords = keywords.filter(
    (keyword) => !normalizedText.includes(normalizeText(keyword)),
  );
  const score = keywords.length
    ? Math.round((matchedKeywords.length / keywords.length) * 100)
    : 0;

  return {
    criterionId: criterion.id,
    title: criterion.title,
    score,
    weight: criterion.weight,
    required: criterion.required,
    matchedKeywords,
    missingKeywords,
  };
}

function splitKeywords(value: string) {
  return value
    .split(/[،,;\n]/)
    .map((keyword) => keyword.trim())
    .filter(Boolean);
}

function normalizeText(value: string) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u064B-\u065F\u0670]/g, "")
    .replace(/[إأآ]/g, "ا")
    .replace(/ى/g, "ي")
    .replace(/ة/g, "ه")
    .replace(/[^\p{L}\p{N}\s.+#-]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function isPdfTextItem(item: unknown): item is { str: string } {
  return (
    typeof item === "object" &&
    item !== null &&
    "str" in item &&
    typeof (item as { str?: unknown }).str === "string"
  );
}

function sortCandidates(first: CandidateResult, second: CandidateResult) {
  const statusScore: Record<CandidateStatus, number> = {
    recommended: 0,
    review: 1,
    excluded: 2,
  };

  return (
    statusScore[first.status] - statusScore[second.status] ||
    second.score - first.score ||
    first.missingRequired.length - second.missingRequired.length
  );
}

function extractEmail(text: string) {
  return text.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i)?.[0] ?? "";
}

function extractPhone(text: string) {
  const match = text.match(/(?:\+?\d[\d\s().-]{7,}\d)/);

  return match?.[0].replace(/\s+/g, " ").trim() ?? "";
}

function createPreview(text: string) {
  const cleanText = text.replace(/\s+/g, " ").trim();

  if (!cleanText) {
    return "لم يتم استخراج نص كاف من هذا الملف.";
  }

  return cleanText.length > 260 ? `${cleanText.slice(0, 260)}...` : cleanText;
}

function isSupportedFile(file: File) {
  return supportedExtensions.includes(getFileExtension(file.name));
}

function getFileExtension(fileName: string) {
  return fileName.split(".").pop()?.toLowerCase() ?? "";
}

function getFileKey(file: File) {
  return `${file.name}-${file.size}-${file.lastModified}`;
}

function formatNumber(value: number) {
  return numberFormatter.format(value);
}

function formatPercent(value: number) {
  return percentFormatter.format(value);
}

function formatFileSize(bytes: number) {
  if (!bytes) {
    return "0 KB";
  }

  const units = ["B", "KB", "MB", "GB"];
  const unitIndex = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** unitIndex;

  return `${numberFormatter.format(Number(value.toFixed(value >= 10 ? 0 : 1)))} ${units[unitIndex]}`;
}

function toCsvRow(values: string[]) {
  return values
    .map((value) => `"${value.replace(/"/g, '""')}"`)
    .join(",");
}

function createId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }

  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
