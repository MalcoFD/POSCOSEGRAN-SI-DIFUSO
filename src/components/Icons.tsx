interface IconProps {
  size?: number
  className?: string
  strokeWidth?: number
  style?: React.CSSProperties
}

const icon = (paths: string | string[], fill = false) =>
  ({ size = 20, className = '', strokeWidth = 1.75, style }: IconProps) => (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={fill ? 'currentColor' : 'none'}
      stroke={fill ? 'none' : 'currentColor'}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={style}
      aria-hidden="true"
    >
      {(Array.isArray(paths) ? paths : [paths]).map((d, i) => (
        <path key={i} d={d} />
      ))}
    </svg>
  )

export const IconHome = icon([
  'M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z',
  'M9 22V12h6v10',
])

export const IconClipboard = icon([
  'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2',
  'M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2',
  'M9 12h6M9 16h4',
])

export const IconPackage = icon([
  'M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z',
  'M3.27 6.96L12 12.01l8.73-5.05M12 22.08V12',
])

export const IconActivity = icon('M22 12h-4l-3 9L9 3l-3 9H2')

export const IconBook = icon([
  'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253',
])

export const IconSettings = icon([
  'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z',
  'M15 12a3 3 0 11-6 0 3 3 0 016 0z',
])

export const IconChevronLeft = icon('M15 19l-7-7 7-7')
export const IconChevronRight = icon('M9 5l7 7-7 7')
export const IconTrending = icon('M23 6l-9.5 9.5-5-5L1 18M17 6h6v6')

export const IconShield = icon([
  'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
])

export const IconPin = icon(['M12 2C8 2 5 5 5 9c0 5 7 13 7 13s7-8 7-13c0-4-3-7-7-7z', 'M12 7a2 2 0 100 4 2 2 0 000-4z'])
export const IconShieldCheck = icon(['M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z', 'M9 12l2 2 4-4'])
export const IconShieldAlert = icon(['M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z', 'M12 8v4M12 16h.01'])
export const IconAlert = icon(['M12 3a9 9 0 100 18 9 9 0 000-18z', 'M12 8v5M12 16h.01'])
export const IconHelp = icon(['M12 3a9 9 0 100 18 9 9 0 000-18z', 'M9.5 9a2.5 2.5 0 113.5 2.3c-.6.3-1 .9-1 1.6V14M12 17h.01'])
export const IconCheck = icon('M20 6L9 17l-5-5')
export const IconX = icon('M6 6l12 12M18 6L6 18')
export const IconPlus = icon('M12 5v14M5 12h14')
export const IconSearch = icon(['M11 4a7 7 0 100 14 7 7 0 000-14z', 'M20 20l-3.5-3.5'])
export const IconCalendar = icon(['M5 5h14a2 2 0 012 2v12a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2z', 'M3 10h18M8 3v4M16 3v4'])
export const IconWrench = icon('M14.7 6.3a4 4 0 00-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 005.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z')
export const IconCode = icon('M8 7l-5 5 5 5M16 7l5 5-5 5')
export const IconCopy = icon(['M11 9h8a2 2 0 012 2v8a2 2 0 01-2 2h-8a2 2 0 01-2-2v-8a2 2 0 012-2z', 'M5 15V5a2 2 0 012-2h10'])
export const IconEye = icon(['M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z', 'M12 9a3 3 0 100 6 3 3 0 000-6z'])
export const IconEyeOff = icon(['M3 3l18 18', 'M10.6 5.1A10 10 0 0112 5c6.5 0 10 7 10 7a17 17 0 01-3.2 4.2M6.6 6.6A17 17 0 002 12s3.5 7 10 7a9.7 9.7 0 005.4-1.6', 'M9.9 9.9a3 3 0 004.2 4.2'])
export const IconThermo = icon('M14 4v10.5a4 4 0 11-4 0V4a2 2 0 014 0z')
export const IconCurve = icon('M3 20L8 6l4 8 3-5 6 11')
export const IconFunnel = icon(['M6 3v6a6 6 0 0012 0V3', 'M12 15v6M8 21h8'])
export const IconChart = icon('M4 20h16M6 16l4-8 4 5 4-9')
export const IconArrowLeft = icon('M15 19l-7-7 7-7')
export const IconLoader = icon('M21 12a9 9 0 11-6.2-8.6')
