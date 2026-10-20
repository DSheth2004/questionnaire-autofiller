import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { BarChart3, ClipboardList, Cpu, MessageSquareText, Moon, ShieldCheck, Sun, Workflow } from "lucide-react";
import { getInfo } from "./api";
import { CountUp, Toast, fadeUp, stagger } from "./ui";
import AskView from "./views/Ask";
import FillView from "./views/Fill";
import EvalView from "./views/Eval";
import HowView from "./views/How";

const TABS = [
  { id: "ask", label: "Ask", icon: MessageSquareText },
  { id: "fill", label: "Fill questionnaire", icon: ClipboardList },
  { id: "eval", label: "Evaluation", icon: BarChart3 },
  { id: "how", label: "How it works", icon: Workflow },
];

function Background() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="blob left-[-10%] top-[-10%] h-[480px] w-[480px] bg-indigo-600/50" />
      <div className="blob right-[-8%] top-[20%] h-[420px] w-[420px] bg-cyan-500/40" style={{ animationDelay: "-6s" }} />
      <div className="blob bottom-[-15%] left-[30%] h-[460px] w-[460px] bg-violet-600/40" style={{ animationDelay: "-12s" }} />
      <div className="absolute inset-0 bg-[radial-gradient(rgba(148,163,184,.12)_1px,transparent_1px)] [background-size:24px_24px]" />
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("ask");
  const [info, setInfo] = useState(null);
  const [mode, setMode] = useState("bm25+expand");
  const [dark, setDark] = useState(() => localStorage.getItem("theme") !== "light");
  const [error, setError] = useState("");
  const clearError = useCallback(() => setError(""), []);

  useEffect(() => {
    getInfo().then(setInfo).catch((e) => setError(`Can't reach the API: ${e.message}`));
  }, []);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try { localStorage.setItem("theme", dark ? "dark" : "light"); } catch {}
  }, [dark]);

  const best = info?.eval?.[mode] || info?.eval?.["bm25+expand"];
  const providers = info?.providers || [];

  return (
    <div className="min-h-screen">
      <Background />

      <header className="sticky top-0 z-30 border-b border-slate-200/60 bg-white/60 backdrop-blur-xl dark:border-white/5 dark:bg-[#070b1a]/60">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2 font-bold">
            <motion.div whileHover={{ rotate: 12, scale: 1.1 }} className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-400 text-white shadow-lg shadow-indigo-500/30">
              <ShieldCheck size={20} />
            </motion.div>
            <span className="hidden sm:inline">Auto-Filler</span>
          </div>
          <nav className="mx-auto flex gap-1 overflow-x-auto rounded-2xl bg-slate-200/60 p-1 dark:bg-white/5">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button key={id} onClick={() => setTab(id)}
                      className={`relative flex items-center gap-2 whitespace-nowrap rounded-xl px-3 py-2 text-sm font-medium transition-colors sm:px-4 ${
                        tab === id ? "text-white" : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"}`}>
                {tab === id && (
                  <motion.span layoutId="tab" className="absolute inset-0 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-500 shadow-lg shadow-indigo-500/25"
                               transition={{ type: "spring", stiffness: 380, damping: 30 }} />
                )}
                <Icon size={16} className="relative" />
                <span className="relative hidden md:inline">{label}</span>
              </button>
            ))}
          </nav>
          <motion.button whileTap={{ scale: 0.85, rotate: 90 }} onClick={() => setDark(!dark)}
                         className="rounded-xl p-2 hover:bg-slate-500/10" aria-label="Toggle theme">
            {dark ? <Sun size={18} /> : <Moon size={18} />}
          </motion.button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 pb-24 sm:px-6">
        <motion.section variants={stagger(0.1)} initial="hidden" animate="show" className="py-12 text-center sm:py-16">
          <motion.div variants={fadeUp} className="mx-auto mb-5 inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-4 py-1.5 text-xs font-medium text-indigo-600 dark:text-indigo-300">
            <Cpu size={14} />
            {providers.length ? `AI drafting via ${providers.map((p) => p.name).join(" → ")}` : "Offline mode · quotes policy text"}
          </motion.div>
          <motion.h1 variants={fadeUp} className="text-4xl font-extrabold tracking-tight sm:text-6xl">
            Security questionnaires,<br /><span className="gradient-text">answered with evidence.</span>
          </motion.h1>
          <motion.p variants={fadeUp} className="mx-auto mt-5 max-w-2xl text-slate-600 dark:text-slate-400">
            Drafts every answer from the company's own policies, cites the exact section behind it, and flags what the
            policies don't cover for a human to answer.
          </motion.p>
          <motion.div variants={fadeUp} className="mx-auto mt-10 grid max-w-3xl grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { v: info?.documents?.length || 0, l: "real policies" },
              { v: info?.chunks || 0, l: "citable sections" },
              { v: (best?.["hit@1"] || 0) * 100, l: "top-1 accuracy", s: "%" },
              { v: (best?.["recall@5"] || 0) * 100, l: "top-5 recall", s: "%" },
            ].map((s) => (
              <motion.div key={s.l} whileHover={{ y: -4 }} className="glass px-4 py-5">
                <div className="text-3xl font-bold"><CountUp value={s.v} suffix={s.s || ""} /></div>
                <div className="mt-1 text-xs text-slate-500">{s.l}</div>
              </motion.div>
            ))}
          </motion.div>
        </motion.section>

        <AnimatePresence mode="wait">
          <motion.div key={tab} initial={{ opacity: 0, y: 20, filter: "blur(6px)" }}
                      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }} exit={{ opacity: 0, y: -12, filter: "blur(6px)" }}
                      transition={{ duration: 0.3 }}>
            {tab === "ask" && <AskView mode={mode} setMode={setMode} info={info} onError={setError} />}
            {tab === "fill" && <FillView mode={mode} info={info} onError={setError} />}
            {tab === "eval" && <EvalView info={info} />}
            {tab === "how" && <HowView info={info} />}
          </motion.div>
        </AnimatePresence>
      </main>

      <footer className="pb-10 text-center text-xs text-slate-500">
        Policies: GitLab Handbook (public) · Questionnaire: Google VSAQ (Apache-2.0)
      </footer>
      <Toast message={error} onClose={clearError} />
    </div>
  );
}
