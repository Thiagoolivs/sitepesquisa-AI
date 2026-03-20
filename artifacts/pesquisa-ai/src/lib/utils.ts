import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Utility to merge Tailwind classes safely
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Calculates a color from Green to Yellow to Red based on a value's position between min and max.
 * Green is used for values closer to min, Yellow for mid-range, and Red for values closer to max.
 */
export function getIntensityColor(value: number, min: number, max: number): string {
  if (isNaN(value) || isNaN(min) || isNaN(max)) return "hsl(221, 83%, 53%)"; // Default Blue
  if (min === max) return "hsl(142, 71%, 45%)"; // Green if no variance

  // Ratio from 0 to 1
  const ratio = Math.max(0, Math.min(1, (value - min) / (max - min)));
  
  // Hue goes from 120 (Green) to 0 (Red)
  const hue = 120 * (1 - ratio);
  
  return `hsl(${hue}, 84%, 50%)`;
}
