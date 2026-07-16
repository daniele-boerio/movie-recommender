import { Star } from 'lucide-react';

export default function StarRating({ value = 0, onChange, max = 10 }) {
  return (
    <div className="star-rating">
      {Array.from({ length: max }, (_, i) => i + 1).map((n) => (
        <button
          key={n}
          className={n <= value ? 'filled' : ''}
          onClick={() => onChange(n)}
          title={`${n}/${max}`}
        >
          <Star size={20} fill={n <= value ? 'currentColor' : 'none'} />
        </button>
      ))}
    </div>
  );
}
