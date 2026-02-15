import { motion } from "framer-motion";
import { ReactNode } from "react";
import { SPRING_CONFIG } from "../constants/animation";
import { useSpringNumber } from "../hooks/useSpringNumber";
import { formatNumberDetailed } from "../utils/format";

interface StatsCardProps {
  title: string;
  value: number;
  type: "number" | "currency";
  subtext?: ReactNode;
  delay?: number;
}

function CountingNumber({ value, type }: { value: number; type: "number" | "currency" }) {
  const text = useSpringNumber(value, {
    type,
    mass: SPRING_CONFIG.mass,
    stiffness: SPRING_CONFIG.stiffness,
    damping: SPRING_CONFIG.damping,
  });

  return <motion.span>{text}</motion.span>;
}

export function StatsCard({ title, value, type, subtext, delay = 0 }: StatsCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay, ease: "easeOut" }}
      className="stats-card"
    >
      <div className="stats-card-head">
        <p>{title}</p>
        <span className="stats-dot" />
      </div>
      <div className="stats-value">
        <CountingNumber value={value} type={type} />
      </div>
      {subtext ? <div className="stats-subtext">{subtext}</div> : null}
      <div className="stats-raw">{formatNumberDetailed(value)}</div>
    </motion.div>
  );
}
