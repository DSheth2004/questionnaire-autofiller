import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { BookOpen, Download, FileSearch, ShieldQuestion, Sparkles } from "lucide-react";
import { fadeUp, stagger } from "../ui";

const STEPS = [
  { icon: BookOpen, title: "Ingest", body: "Policy Markdown is cleaned and split by heading into citable sections. Each keeps its title, heading path and public URL." },
  { icon: FileSearch, title: "Retrieve", body: "BM25 keyword search plus a compliance synonym map that turns questionnaire wording (\"malware\") into policy wording (\"endpoint detection and response\")." },
  { icon: ShieldQuestion, title: "Gate", body: "If even the best section matches weakly, the question is flagged for human review instead of being answered." },
  { icon: Sparkles, title: "Draft", body: "An LLM (Gemini → Groq → Ollama → Claude, whichever is available) answers only from the top 5 sections and must cite them. Low confidence or no citation goes to review." },
  { icon: Download, title: "Export", body: "The filled questionnaire downloads as Excel, with review rows highlighted and every citation linked." },
];

export default function HowView({ info }) {
  const [active, setActive] = useState(0);
  const step = STEPS[active];
  return (
    <div className="space-y-8">
      <div className="relative">
        <div className="absolute left-0 right-0 top-7 hidden h-0.5 bg-slate-200 md:block dark:bg-white/10" />
        <motion.div className="absolute left-0 top-7 hidden h-0.5 bg-gradient-to-r from-indigo-500 to-cyan-400 md:block"
                    animate={{ width: `${(active / (STEPS.length - 1)) * 100}%` }} transition={{ type: "spring", stiffness: 120, damping: 20 }} />
        <motion.div variants={stagger(0.08)} initial="hidden" animate="show" className="relative grid grid-cols-5 gap-2">
          {STEPS.map((s, i) => (
            <motion.button key={s.title} variants={fadeUp} onClick={() => setActive(i)} onMouseEnter={() => setActive(i)}
                           className="flex flex-col items-center gap-2 text-center">
              <motion.div animate={{ scale: i === active ? 1.15 : 1 }}
                          className={`grid h-14 w-14 place-items-center rounded-2xl border transition-colors ${
                            i <= active ? "border-transparent bg-gradient-to-br from-indigo-500 to-cyan-400 text-white shadow-lg shadow-indigo-500/30"
                                        : "border-slate-300 bg-white text-slate-400 dark:border-white/10 dark:bg-[#0b1024]"}`}>
                <s.icon size={22} />
              </motion.div>
              <span className={`text-sm font-semibold ${i === active ? "" : "text-slate-500"}`}>{i + 1}. {s.title}</span>
            </motion.button>
          ))}
        </motion.div>
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={active} initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -30 }}
                    transition={{ duration: 0.25 }} className="glass flex items-start gap-5 p-8">
          <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-indigo-500/15 text-indigo-500"><step.icon size={24} /></div>
          <div>
            <h3 className="text-xl font-bold">{active + 1}. {step.title}</h3>
            <p className="mt-2 leading-relaxed text-slate-600 dark:text-slate-400">{step.body}</p>
          </div>
        </motion.div>
      </AnimatePresence>

      <motion.div variants={fadeUp} initial="hidden" animate="show" className="glass p-6">
        <h3 className="mb-3 font-semibold">Policy library · {info?.documents?.length ?? 0} documents</h3>
        <motion.div variants={stagger(0.02)} initial="hidden" animate="show" className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {(info?.documents || []).map((d) => (
            <motion.a key={d.url} variants={fadeUp} whileHover={{ y: -2 }} href={d.url} target="_blank" rel="noreferrer"
                      className="flex items-center justify-between gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm transition-colors hover:border-indigo-400 dark:border-white/10">
              <span className="truncate">{d.title}</span>
              <span className="shrink-0 rounded-full bg-slate-500/10 px-2 text-xs text-slate-500">{d.sections}</span>
            </motion.a>
          ))}
        </motion.div>
      </motion.div>
    </div>
  );
}
