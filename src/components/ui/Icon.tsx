import { SymbolView, type SFSymbol, type SymbolWeight } from 'expo-symbols';
import { View } from 'react-native';

type Props = {
  name: SFSymbol;
  size?: number;
  color: string;
  weight?: SymbolWeight;
};

/** SF Symbol on iOS; a neutral dot where SF Symbols are unavailable (Android/web). */
export function Icon({ name, size = 20, color, weight = 'semibold' }: Props) {
  return (
    <SymbolView
      name={name}
      size={size}
      tintColor={color}
      weight={weight}
      type="hierarchical"
      fallback={
        <View
          style={{
            width: size * 0.5,
            height: size * 0.5,
            borderRadius: size,
            backgroundColor: color,
            margin: size * 0.25,
          }}
        />
      }
    />
  );
}
