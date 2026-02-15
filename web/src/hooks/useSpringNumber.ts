import { MotionValue, useSpring, useTransform } from "framer-motion";
import { useEffect } from "react";
import { SPRING_CONFIG } from "../constants/animation";
import { formatCurrency, formatNumberCompact } from "../utils/format";

interface UseSpringNumberOptions {
  type: "number" | "currency";
  stiffness?: number;
  damping?: number;
  mass?: number;
}

export function useSpringNumber(value: number, options: UseSpringNumberOptions): MotionValue<string> {
  const spring = useSpring(0, {
    stiffness: options.stiffness ?? SPRING_CONFIG.stiffness,
    damping: options.damping ?? SPRING_CONFIG.damping,
    mass: options.mass ?? SPRING_CONFIG.mass,
  });

  const text = useTransform(spring, (current) => {
    if (options.type === "currency") {
      return formatCurrency(current);
    }
    return formatNumberCompact(current);
  });

  useEffect(() => {
    spring.set(value);
  }, [spring, value]);

  return text;
}
