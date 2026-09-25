import type { ReactNode, SVGProps } from "react";

type IconProps = Omit<SVGProps<SVGSVGElement>, "children"> & { size?: number };

function Svg({ size = 16, children, ...rest }: IconProps & { children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.4}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {children}
    </svg>
  );
}

export const Icon = {
  Overview: (p: IconProps) => (
    <Svg {...p}>
      <rect x="2" y="2" width="5" height="5" rx="1" />
      <rect x="9" y="2" width="5" height="5" rx="1" />
      <rect x="2" y="9" width="5" height="5" rx="1" />
      <rect x="9" y="9" width="5" height="5" rx="1" />
    </Svg>
  ),
  Customers: (p: IconProps) => (
    <Svg {...p}>
      <circle cx="8" cy="5.5" r="2.5" />
      <path d="M3 13.5c.8-2.3 2.7-3.5 5-3.5s4.2 1.2 5 3.5" />
    </Svg>
  ),
  Segments: (p: IconProps) => (
    <Svg {...p}>
      <circle cx="6" cy="8" r="4" />
      <circle cx="10" cy="8" r="4" />
    </Svg>
  ),
  Analytics: (p: IconProps) => (
    <Svg {...p}>
      <path d="M2.5 13.5h11" />
      <path d="M4.5 11V8" />
      <path d="M8 11V4.5" />
      <path d="M11.5 11V6.5" />
    </Svg>
  ),
  Quality: (p: IconProps) => (
    <Svg {...p}>
      <path d="M8 1.8 13 3.6v4.1c0 3-2.1 5.3-5 6.5-2.9-1.2-5-3.5-5-6.5V3.6L8 1.8Z" />
      <path d="m5.8 8 1.5 1.5 3-3" />
    </Svg>
  ),
  Pipeline: (p: IconProps) => (
    <Svg {...p}>
      <circle cx="3" cy="8" r="1.75" />
      <circle cx="8" cy="8" r="1.75" />
      <circle cx="13" cy="8" r="1.75" />
      <path d="M4.75 8h1.5M9.75 8h1.5" />
    </Svg>
  ),
  Health: (p: IconProps) => (
    <Svg {...p}>
      <path d="M1.5 8.5h3l1.5-4 3 8 1.5-4h4" />
    </Svg>
  ),
  Search: (p: IconProps) => (
    <Svg {...p}>
      <circle cx="7" cy="7" r="4.25" />
      <path d="m10.2 10.2 3.3 3.3" />
    </Svg>
  ),
  ChevronRight: (p: IconProps) => (
    <Svg {...p}>
      <path d="m6 3.5 4.5 4.5L6 12.5" />
    </Svg>
  ),
  ArrowLeft: (p: IconProps) => (
    <Svg {...p}>
      <path d="M13 8H3.5M7.5 4 3.5 8l4 4" />
    </Svg>
  ),
  Menu: (p: IconProps) => (
    <Svg {...p}>
      <path d="M2.5 4.5h11M2.5 8h11M2.5 11.5h11" />
    </Svg>
  ),
  Close: (p: IconProps) => (
    <Svg {...p}>
      <path d="m4 4 8 8M12 4l-8 8" />
    </Svg>
  ),
  File: (p: IconProps) => (
    <Svg {...p}>
      <path d="M9.5 1.75H4.25c-.55 0-1 .45-1 1v10.5c0 .55.45 1 1 1h7.5c.55 0 1-.45 1-1V5L9.5 1.75Z" />
      <path d="M9.5 1.75V5h3.25" />
    </Svg>
  ),
  Database: (p: IconProps) => (
    <Svg {...p}>
      <ellipse cx="8" cy="3.75" rx="5" ry="2" />
      <path d="M3 3.75v8.5c0 1.1 2.24 2 5 2s5-.9 5-2v-8.5" />
      <path d="M3 8c0 1.1 2.24 2 5 2s5-.9 5-2" />
    </Svg>
  ),
  Check: (p: IconProps) => (
    <Svg {...p}>
      <path d="m3.5 8.5 3 3 6-7" />
    </Svg>
  ),
  Denied: (p: IconProps) => (
    <Svg {...p}>
      <circle cx="8" cy="8" r="5.75" />
      <path d="m4 12 8-8" />
    </Svg>
  ),
  Alert: (p: IconProps) => (
    <Svg {...p}>
      <path d="M8 2.2 14.2 13H1.8L8 2.2Z" />
      <path d="M8 6.5v3" />
      <path d="M8 11.3v.2" />
    </Svg>
  ),
  Info: (p: IconProps) => (
    <Svg {...p}>
      <circle cx="8" cy="8" r="6" />
      <path d="M8 7.2v3.6M8 5v.2" />
    </Svg>
  ),
  Prompt: (p: IconProps) => (
    <Svg {...p}>
      <rect x="1.75" y="2.5" width="12.5" height="11" rx="1.5" />
      <path d="m4.5 6.5 2 1.75-2 1.75" />
      <path d="M8 10.5h3.5" />
    </Svg>
  ),
  Route: (p: IconProps) => (
    <Svg {...p}>
      <path d="M3 2.5v5c0 1.1.9 2 2 2h7" />
      <path d="m10 7.5 2 2-2 2" />
    </Svg>
  ),
  Logout: (p: IconProps) => (
    <Svg {...p}>
      <path d="M6 13.5H3.5c-.55 0-1-.45-1-1v-9c0-.55.45-1 1-1H6" />
      <path d="M10.5 11 13.5 8l-3-3M13.5 8H6" />
    </Svg>
  ),
  Refresh: (p: IconProps) => (
    <Svg {...p}>
      <path d="M13.5 8a5.5 5.5 0 1 1-1.6-3.9" />
      <path d="M13.5 2.5v3h-3" />
    </Svg>
  ),
};
