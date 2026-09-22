# MY-CV — AI CV Screening Platform

Arabic RTL dashboard for bulk CV screening against custom company criteria.
Processes 500+ CVs locally in the browser — no data leaves the device.

## Features
- Upload PDF, DOCX, TXT in bulk (up to 500 files)
- Custom criteria with weights and required flags
- Keyword-based scoring + ranked results
- Export shortlist as CSV
- Optional server-side LLM extraction (GPT-4o-mini)

## Run locally
```bash
cd app
npm install
npm run dev
```

## Build
```bash
npm run build
```

## LLM extraction (optional)
Copy `.env.example` to `.env` and fill in your API key.
The LLM layer runs server-side only — never exposed to the browser.

## Stack
- React 19 + TypeScript + Vite
- Tailwind CSS 4
- pdfjs-dist (PDF extraction)
- mammoth (DOCX extraction)
- GPT-4o-mini (optional server-side LLM)
