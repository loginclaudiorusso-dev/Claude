import {
  Activity, CalendarHeart, Compass, Flame, HeartHandshake, Leaf, Medal, Shapes, Snowflake, Sparkles, Sunrise, Swords, Trophy, Users, Target,
  type LucideProps,
} from 'lucide-react';

const MAP = { Activity, CalendarHeart, Compass, Flame, HeartHandshake, Leaf, Medal, Shapes, Snowflake, Sparkles, Sunrise, Swords, Trophy, Users, Target };
export const ICON_NAMES = Object.keys(MAP) as (keyof typeof MAP)[];

/** Icon über seinen Namen (für Challenges und Abzeichen, deren Icon in den Daten steht). */
export function DynIcon({ name, ...props }: { name: string } & LucideProps) {
  const C = MAP[name as keyof typeof MAP] ?? Target;
  return <C aria-hidden {...props} />;
}
