import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Loader2, Search, Sparkles } from "lucide-react";
import { ask } from "../api";
import { Accordion, AnswerCard, Bar, fadeUp, stagger } from "../ui";

const EXAMPLES = [
  "Do you require multi-factor authentication?",
  "How long are security logs retained?",
  "Is a third-party penetration test performed annually?",
  "Do you encrypt laptop hard disks?",
  "Do you place externally exposed systems in a DMZ?",
];

export default function AskView({ mode, setMode, info, onError }) {
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const inputRef = useRef(null);

  // Ctrl/Cmd+K focuses the search box
  useEffect(() => {
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); inputRef.current?.focus(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  async function run(question) {
    const text = (question ?? q).trim();
    if (!text) return;
    setQ(text);
    setLoading(true);
    try {
      setData(await ask(text, mode));
    } catch (e) {
      onError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={(e) => { e.preventDefault(); run(); }}
            className="glass group flex items-center gap-3 p-2 pl-5 transition-shadow focus-within:shadow-xl focus-within:shadow-indigo-500/20 focus-within:ring-2 focus-within:ring-indigo-500/40">
        <Search size={20} className="shrink-0 text-slate-400" />
        <input ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)}
               placeholder="Ask any security questionnaire question…"
               className="min-w-0 flex-1 bg-transparent py-3 text-base outline-none placeholder:text-slate-400" />
        <kbd className="hidden rounded-md border border-slate-300 px-2 py-0.5 text-xs text-slate-400 sm:block dark:border-white/10">Ctrl K</kbd>
        <select value={mode} onChange={(e) => setMode(e.target.value)}
                className="hidden rounded-lg bg-slate-100 px-2 py-2 text-xs outline-none md:block dark:bg-white/5">
          {(info?.modes || []).map((m) => <option key={m.id} value={m.id} className="text-slate-900">{m.label}</option>)}
        </select>
        <motion.button whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.95 }} disabled={loading}
                       className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-500 px-5 py-3 font-semibold text-white shadow-lg shadow-indigo-500/30 disabled:opacity-60">
          {loading ? <Loader2 size={18} className="animate-spin" /> : <Sparkles size={18} />}
          <span className="hidden sm:inline">Answer</span>
        </motion.button>
      </form>

      <motion.div variants={stagger(0.05)} initial="hidden" animate="show" className="flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <motion.button key={ex} variants={fadeUp} whileHover={{ y: -2 }} whileTap={{ scale: 0.97 }}
                         onClick={() => run(ex)}
                         className="flex items-center gap-1.5 rounded-full border border-slate-300 bg-white/60 px-4 py-2 text-sm text-slate-600 transition-colors hover:border-indigo-400 hover:text-indigo-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-300 dark:hover:text-white">
            {ex} <ArrowRight size={14} className="opacity-50" />
          </motion.button>
        ))}
      </motion.div>

      <AnimatePresence mode="wait">
        {loading && !data && (
          <motion.div key="skeleton" exit={{ opacity: 0 }} className="grid gap-6 lg:grid-cols-5">
            <div className="glass shimmer h-64 lg:col-span-3" />
            <div className="glass shimmer h-64 lg:col-span-2" />
          </motion.div>
        )}
        {data && (
          <motion.div key={data.result.question} initial={{ opacity: 0 }} animate={{ opacity: loading ? 0.5 : 1 }} exit={{ opacity: 0 }}
                      className="grid gap-6 lg:grid-cols-5">
            <div className="lg:col-span-3">
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-500">Drafted answer</h3>
              <AnswerCard result={data.result} />
            </div>
            <div className="lg:col-span-2">
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-500">Top matching sections</h3>
              <motion.div variants={stagger(0.07)} initial="hidden" animate="show" className="space-y-3">
                {data.hits.map((h, i) => (
                  <motion.div key={i} variants={fadeUp} whileHover={{ scale: 1.01 }} className="glass p-4">
                    <div className="flex items-baseline justify-between gap-2">
                      <a href={h.url} target="_blank" rel="noreferrer" className="font-semibold hover:text-indigo-500">{h.title}</a>
                      <span className="text-xs tabular-nums text-slate-500">{Math.round(h.score * 100)}</span>
                    </div>
                    <div className="mb-2 truncate text-xs text-slate-500">{h.section}</div>
                    <Bar value={h.score} delay={0.1 + i * 0.08} />
                    <div className="mt-3"><Accordion title="Read section">{h.text}</Accordion></div>
                  </motion.div>
                ))}
              </motion.div>
            </div>
          </motion.div>
        )}
        {!data && !loading && (
          <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                      className="glass grid place-items-center py-16 text-center">
            <motion.div animate={{ y: [0, -8, 0] }} transition={{ repeat: Infinity, duration: 3 }}>
              <Sparkles size={40} className="mx-auto text-indigo-400" />
            </motion.div>
            <p className="mt-4 text-slate-500">Pick an example above or type your own question.</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
