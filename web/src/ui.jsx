import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, animate, motion, useInView } from "framer-motion";
import { CheckCircle2, ChevronDown, ExternalLink, FileText, Flag, X } from "lucide-react";

export const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 260, damping: 26 } },
};
export const stagger = (gap = 0.06) => ({ hidden: {}, show: { transition: { staggerChildren: gap } } });

/** Number that counts up when it scrolls into view. */
export function CountUp({ value, decimals = 0, suffix = "", duration = 1.2 }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });
  const [shown, setShown] = useState(0);
  useEffect(() => {
    if (!inView) return;
    const controls = animate(0, value, { duration, ease: "easeOut", onUpdate: setShown });
    return () => controls.stop();
  }, [inView, value, duration]);
  return <span ref={ref}>{shown.toFixed(decimals)}{suffix}</span>;
}

const BADGE = {
  Yes: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300 ring-emerald-500/30",
  No: "bg-rose-500/15 text-rose-600 dark:text-rose-300 ring-rose-500/30",
  Partial: "bg-amber-500/15 text-amber-700 dark:text-amber-300 ring-amber-500/30",
  "Not covered": "bg-slate-500/15 text-slate-600 dark:text-slate-300 ring-slate-500/30",
  "See policy": "bg-indigo-500/15 text-indigo-600 dark:text-indigo-300 ring-indigo-500/30",
};

export function AnswerBadge({ answer }) {
  return (
    <span className={`inline-flex items-center whitespace-nowrap rounded-full px-3 py-1 text-xs font-semibold ring-1 ${BADGE[answer] || BADGE["See policy"]}`}>
      {answer}
    </span>
  );
}

export function StatusBadge({ status }) {
  const ok = status === "Drafted";
  const Icon = ok ? CheckCircle2 : Flag;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
      ok ? "bg-emerald-500/15 text-emerald-600 ring-emerald-500/30 dark:text-emerald-300"
         : "bg-amber-500/15 text-amber-700 ring-amber-500/30 dark:text-amber-300"}`}>
      <Icon size={13} /> {status}
    </span>
  );
}

export const confColour = (c) => (c >= 0.7 ? "#10b981" : c >= 0.4 ? "#f59e0b" : "#f43f5e");

/** Animated circular gauge. */
export function ConfidenceRing({ value, size = 96 }) {
  const r = size / 2 - 7;
  const circ = 2 * Math.PI * r;
  const v = Math.min(Math.max(value, 0), 1);
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="currentColor" strokeWidth="7" fill="none" className="text-slate-200 dark:text-white/10" />
        <motion.circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={confColour(v)} strokeWidth="7" strokeLinecap="round"
          strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: circ * (1 - v) }}
          transition={{ duration: 1, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <div className="text-lg font-bold"><CountUp value={v * 100} suffix="%" duration={1} /></div>
          <div className="-mt-0.5 text-[9px] uppercase tracking-wide text-slate-500">confidence</div>
        </div>
      </div>
    </div>
  );
}

export function Bar({ value, colour, delay = 0, className = "h-2" }) {
  return (
    <div className={`w-full overflow-hidden rounded-full bg-slate-200 dark:bg-white/10 ${className}`}>
      <motion.div
        className="h-full rounded-full"
        style={{ background: colour || "linear-gradient(90deg,#6366f1,#22d3ee)" }}
        initial={{ width: 0 }}
        animate={{ width: `${Math.min(value, 1) * 100}%` }}
        transition={{ duration: 0.9, delay, ease: "easeOut" }}
      />
    </div>
  );
}

export function Citation({ c, i = 0 }) {
  return (
    <motion.a
      href={c.url} target="_blank" rel="noreferrer"
      variants={fadeUp}
      whileHover={{ x: 4 }}
      className="group flex items-start gap-3 rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-3 transition-colors hover:border-indigo-500/50 hover:bg-indigo-500/10"
    >
      <FileText size={18} className="mt-0.5 shrink-0 text-indigo-500" />
      <div className="min-w-0 flex-1">
        <div className="font-semibold text-slate-800 dark:text-slate-100">{c.title}</div>
        <div className="truncate text-xs text-slate-500">{c.section}</div>
      </div>
      <ExternalLink size={15} className="mt-1 shrink-0 text-slate-400 opacity-0 transition-opacity group-hover:opacity-100" />
    </motion.a>
  );
}

/** The drafted-answer card used by both the Ask view and the row drawer. */
export function AnswerCard({ result }) {
  return (
    <motion.div variants={stagger(0.08)} initial="hidden" animate="show" className="glass p-6">
      <motion.div variants={fadeUp} className="flex items-start justify-between gap-4">
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <AnswerBadge answer={result.answer} />
            <StatusBadge status={result.status} />
            {result.mode && result.mode !== "abstain" && (
              <span className="rounded-full bg-slate-500/10 px-3 py-1 text-xs text-slate-500">
                {result.mode === "extractive" ? "Quoted from policy" : `Written by ${result.mode}`}
              </span>
            )}
          </div>
          <p className="leading-relaxed text-slate-700 dark:text-slate-300">{result.explanation}</p>
        </div>
        <ConfidenceRing value={result.confidence} />
      </motion.div>
      <motion.div variants={fadeUp} className="mt-5 mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
        Evidence
      </motion.div>
      <div className="space-y-2">
        {result.citations.map((c, i) => <Citation key={c.chunk_id || i} c={c} i={i} />)}
      </div>
    </motion.div>
  );
}

export function Accordion({ title, children }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button onClick={() => setOpen(!open)} className="flex items-center gap-1 text-xs font-medium text-indigo-500 hover:text-indigo-400">
        {title}
        <motion.span animate={{ rotate: open ? 180 : 0 }}><ChevronDown size={14} /></motion.span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }} className="overflow-hidden"
          >
            <div className="mt-2 max-h-60 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-100 p-3 text-xs leading-relaxed text-slate-600 dark:bg-black/30 dark:text-slate-400">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/** Animated pill selector (the active pill slides between options). */
export function Segmented({ options, value, onChange, id }) {
  return (
    <div className="inline-flex rounded-xl bg-slate-200/70 p-1 dark:bg-white/5">
      {options.map((o) => (
        <button
          key={o.value} onClick={() => onChange(o.value)}
          className={`relative rounded-lg px-4 py-1.5 text-sm font-medium transition-colors ${
            value === o.value ? "text-white" : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"}`}
        >
          {value === o.value && (
            <motion.span layoutId={id} className="absolute inset-0 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 shadow"
                         transition={{ type: "spring", stiffness: 400, damping: 32 }} />
          )}
          <span className="relative">{o.label}</span>
        </button>
      ))}
    </div>
  );
}

export function Drawer({ open, onClose, children }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  // portal: the page transition applies a CSS filter, which would otherwise trap position:fixed
  return createPortal(
    <AnimatePresence>
      {open && (
        <>
          <motion.div className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm" onClick={onClose}
                      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
          <motion.aside
            className="fixed right-0 top-0 z-50 h-full w-full max-w-xl overflow-y-auto border-l border-white/10 bg-slate-50 p-6 dark:bg-[#0b1024]"
            initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 300, damping: 34 }}
          >
            <button onClick={onClose} className="mb-4 rounded-lg p-2 hover:bg-slate-500/10" aria-label="Close"><X size={18} /></button>
            {children}
          </motion.aside>
        </>
      )}
    </AnimatePresence>,
    document.body
  );
}

export function Toast({ message, onClose }) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onClose, 5000);
    return () => clearTimeout(t);
  }, [message, onClose]);
  return (
    <AnimatePresence>
      {message && (
        <motion.div
          initial={{ y: 40, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 40, opacity: 0 }}
          className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-xl bg-rose-600 px-5 py-3 text-sm font-medium text-white shadow-xl"
        >
          {message}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
