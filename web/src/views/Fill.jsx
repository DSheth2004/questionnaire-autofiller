import { useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Download, FileSpreadsheet, Flag, Gauge, Loader2, Play, Search, Square, UploadCloud } from "lucide-react";
import { exportXlsx, fill } from "../api";
import { AnswerBadge, AnswerCard, CountUp, Drawer, Segmented, confColour, fadeUp, stagger } from "../ui";

function Stat({ icon: Icon, value, label, tint, suffix = "" }) {
  return (
    <motion.div variants={fadeUp} whileHover={{ y: -4 }} className="glass flex items-center gap-4 p-5">
      <div className={`grid h-11 w-11 place-items-center rounded-xl ${tint}`}><Icon size={20} /></div>
      <div>
        <div className="text-2xl font-bold tabular-nums"><CountUp value={value} suffix={suffix} duration={0.6} /></div>
        <div className="text-xs text-slate-500">{label}</div>
      </div>
    </motion.div>
  );
}

export default function FillView({ mode, info, onError }) {
  const [file, setFile] = useState(null);
  const [drag, setDrag] = useState(false);
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [running, setRunning] = useState(false);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(null);
  const abortRef = useRef(null);
  const inputRef = useRef(null);

  async function start() {
    setRows([]); setTotal(0); setRunning(true);
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    const buffer = [];
    let flush = null;
    try {
      await fill(file, mode, (ev) => {
        if (ev.type === "start") setTotal(ev.total);
        if (ev.type === "row") {
          // batch rows per animation frame so a fast stream stays smooth
          buffer.push(ev.row);
          flush ??= requestAnimationFrame(() => { setRows((r) => [...r, ...buffer.splice(0)]); flush = null; });
        }
      }, ctrl.signal);
    } catch (e) {
      if (e.name !== "AbortError") onError(e.message);
    } finally {
      setTimeout(() => { setRows((r) => [...r, ...buffer.splice(0)]); setRunning(false); }, 50);
    }
  }

  const counts = useMemo(() => ({
    drafted: rows.filter((r) => r.status === "Drafted").length,
    review: rows.filter((r) => r.status !== "Drafted").length,
    avg: rows.length ? rows.reduce((s, r) => s + r.confidence, 0) / rows.length : 0,
  }), [rows]);

  const shown = rows.filter((r) =>
    (filter === "all" || (filter === "drafted" ? r.status === "Drafted" : r.status !== "Drafted")) &&
    r.question.toLowerCase().includes(search.toLowerCase()));
  const progress = total ? rows.length / total : 0;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-5">
        <motion.div
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) setFile(f); }}
          onClick={() => inputRef.current?.click()}
          animate={{ scale: drag ? 1.02 : 1, borderColor: drag ? "#6366f1" : "rgba(148,163,184,.35)" }}
          className="glass flex cursor-pointer flex-col items-center justify-center gap-3 border-2 border-dashed p-8 text-center md:col-span-3"
        >
          <input ref={inputRef} type="file" accept=".xlsx" hidden onChange={(e) => e.target.files[0] && setFile(e.target.files[0])} />
          <motion.div animate={{ y: drag ? -6 : 0 }}><UploadCloud size={40} className="text-indigo-400" /></motion.div>
          {file ? (
            <div className="flex items-center gap-2 font-semibold"><FileSpreadsheet size={18} className="text-emerald-500" /> {file.name}
              <button onClick={(e) => { e.stopPropagation(); setFile(null); }} className="ml-2 text-xs text-slate-500 underline">remove</button>
            </div>
          ) : (
            <>
              <div className="font-semibold">Drop a questionnaire here, or click to browse</div>
              <div className="text-sm text-slate-500">.xlsx with a <b>Question</b> column. No file? The sample is used.</div>
            </>
          )}
        </motion.div>

        <div className="glass flex flex-col justify-between gap-4 p-6 md:col-span-2">
          <div>
            <div className="text-sm text-slate-500">Questionnaire</div>
            <div className="mt-1 font-semibold">{file ? file.name : `Google VSAQ sample · ${info?.sample_questions ?? 126} real questions`}</div>
            {!file && <a href="/api/sample" className="text-xs text-indigo-500 hover:underline">Download the sample .xlsx</a>}
          </div>
          {running ? (
            <motion.button whileTap={{ scale: 0.96 }} onClick={() => abortRef.current?.abort()}
                           className="flex items-center justify-center gap-2 rounded-xl bg-slate-800 px-5 py-3 font-semibold text-white dark:bg-white/10">
              <Square size={16} /> Stop
            </motion.button>
          ) : (
            <motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.96 }} onClick={start}
                           className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-500 px-5 py-3 font-semibold text-white shadow-lg shadow-indigo-500/30">
              <Play size={16} /> Fill questionnaire
            </motion.button>
          )}
        </div>
      </div>

      <AnimatePresence>
        {(running || rows.length > 0) && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="space-y-6">
            <div className="glass p-5">
              <div className="mb-2 flex justify-between text-sm">
                <span className="flex items-center gap-2 font-medium">
                  {running ? <Loader2 size={16} className="animate-spin text-indigo-500" /> : <CheckCircle2 size={16} className="text-emerald-500" />}
                  {running ? "Answering questions…" : "Done"}
                </span>
                <span className="tabular-nums text-slate-500">{rows.length} / {total}</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-slate-200 dark:bg-white/10">
                <motion.div className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-violet-500 to-cyan-400"
                            animate={{ width: `${progress * 100}%` }} transition={{ ease: "easeOut" }} />
              </div>
            </div>

            <motion.div variants={stagger(0.08)} initial="hidden" animate="show" className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <Stat icon={FileSpreadsheet} value={rows.length} label="Questions answered" tint="bg-indigo-500/15 text-indigo-500" />
              <Stat icon={CheckCircle2} value={counts.drafted} label="Drafted" tint="bg-emerald-500/15 text-emerald-500" />
              <Stat icon={Flag} value={counts.review} label="Needs human review" tint="bg-amber-500/15 text-amber-500" />
              <Stat icon={Gauge} value={counts.avg * 100} suffix="%" label="Average confidence" tint="bg-cyan-500/15 text-cyan-500" />
            </motion.div>

            <div className="glass overflow-hidden">
              <div className="flex flex-wrap items-center gap-3 border-b border-slate-200 p-4 dark:border-white/5">
                <Segmented id="filter" value={filter} onChange={setFilter} options={[
                  { value: "all", label: `All ${rows.length}` },
                  { value: "drafted", label: `Drafted ${counts.drafted}` },
                  { value: "review", label: `Review ${counts.review}` },
                ]} />
                <div className="flex min-w-[200px] flex-1 items-center gap-2 rounded-xl bg-slate-100 px-3 py-2 dark:bg-white/5">
                  <Search size={16} className="text-slate-400" />
                  <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search questions…"
                         className="w-full bg-transparent text-sm outline-none" />
                </div>
                <motion.button whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.95 }} disabled={running || !rows.length}
                               onClick={() => exportXlsx(rows).catch((e) => onError(e.message))}
                               className="flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-emerald-500/25 disabled:opacity-50">
                  <Download size={16} /> Export Excel
                </motion.button>
              </div>
              <div className="max-h-[560px] overflow-auto">
                <table className="w-full text-left text-sm">
                  <thead className="sticky top-0 z-10 bg-slate-100/95 text-xs uppercase tracking-wider text-slate-500 backdrop-blur dark:bg-[#0d1328]/95">
                    <tr>
                      <th className="px-4 py-3">Question</th>
                      <th className="px-4 py-3">Answer</th>
                      <th className="px-4 py-3 w-40">Confidence</th>
                      <th className="px-4 py-3 hidden lg:table-cell">Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    <AnimatePresence initial={false}>
                      {shown.map((r) => (
                        <motion.tr key={r.id} layout initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }}
                                   exit={{ opacity: 0 }} transition={{ duration: 0.25 }}
                                   onClick={() => setSelected(r)}
                                   className="cursor-pointer border-t border-slate-200/70 transition-colors hover:bg-indigo-500/5 dark:border-white/5">
                          <td className="px-4 py-3">
                            <div className="flex items-start gap-2">
                              {r.status === "Drafted"
                                ? <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-emerald-500" />
                                : <Flag size={16} className="mt-0.5 shrink-0 text-amber-500" />}
                              <div>
                                <div className="line-clamp-2">{r.question}</div>
                                <div className="text-xs text-slate-500">{r.id}</div>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3"><AnswerBadge answer={r.answer} /></td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-200 dark:bg-white/10">
                                <div className="h-full rounded-full" style={{ width: `${Math.min(r.confidence, 1) * 100}%`, background: confColour(r.confidence) }} />
                              </div>
                              <span className="tabular-nums text-xs text-slate-500">{Math.round(Math.min(r.confidence, 1) * 100)}%</span>
                            </div>
                          </td>
                          <td className="hidden max-w-[220px] truncate px-4 py-3 text-slate-500 lg:table-cell">{r.citations[0]?.title}</td>
                        </motion.tr>
                      ))}
                    </AnimatePresence>
                  </tbody>
                </table>
                {!shown.length && !running && <div className="p-10 text-center text-slate-500">No questions match.</div>}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <Drawer open={!!selected} onClose={() => setSelected(null)}>
        {selected && (
          <div className="space-y-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">{selected.id} · {selected.section}</div>
            <h3 className="text-xl font-bold leading-snug">{selected.question}</h3>
            <AnswerCard result={selected} />
          </div>
        )}
      </Drawer>
    </div>
  );
}
