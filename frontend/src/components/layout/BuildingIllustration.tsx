export function BuildingIllustration({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 520 320" fill="none" className={className} aria-hidden="true">
      <g strokeWidth="1.2" strokeLinejoin="round" className="stroke-primary/30">
        <path d="M50 230 260 120 470 230 260 340Z" className="fill-primary/5" />
        <path d="M210 100 310 48 412 100 312 154Z" className="fill-card" />
        <path d="M210 100v132l102 54V154Z" className="fill-primary/10" />
        <path d="M312 154 412 100v132l-100 54Z" className="fill-primary/20" />
        <path d="m80 163 103-53 103 54-104 55Z" className="fill-card" />
        <path d="M80 163v66l102 54v-64Z" className="fill-primary/10" />
        <path d="m182 219 104-55v65l-104 54Z" className="fill-primary/20" />
        <path d="m210 132 102 55 100-54M210 165l102 54 100-54M210 198l102 55 100-54M80 196l102 54 104-55" />
        <path d="M237 115v130m25-117v130m25-116v129m50-130v132m25-145v131m25-145v132M105 176v66m25-53v66m25-52v66m53-65v65m26-79v65m26-78v65" />
        <path
          strokeDasharray="4 5"
          d="m50 250 132 70M430 100l35-18M310 28V8M68 157l-35-18"
        />
        <circle cx="465" cy="82" r="4" className="fill-primary/40" />
        <circle cx="310" cy="8" r="4" className="fill-primary/40" />
      </g>
    </svg>
  );
}
