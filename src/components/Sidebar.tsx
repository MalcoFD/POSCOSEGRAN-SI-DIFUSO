import { View } from '../types'
import { Skeleton } from './Shared'
import {
  IconHome,
  IconClipboard,
  IconActivity,
  IconBook,
  IconPackage,
  IconShield,
  IconTrending,
  IconSettings,
  IconChevronLeft,
  IconChevronRight,
  IconPin,
} from './Icons'

interface SidebarProps {
  activeView: View
  onNavigate: (view: View) => void
  collapsed: boolean
  onToggle: () => void
  roles: string[]
  cargando?: boolean
}

// `roles` vacío: visible para todos. Si no, solo para esos roles.
const NAV_ITEMS: { id: View; label: string; Icon: React.FC<{ size?: number; className?: string }>; roles?: string[] }[] = [
  { id: 'dashboard', label: 'Inicio', Icon: IconHome },
  { id: 'almacenes', label: 'Almacenes y lotes', Icon: IconPackage, roles: ['PRODUCTOR', 'TECNICO'] },
  { id: 'evaluacion', label: 'Evaluaciones', Icon: IconClipboard, roles: ['PRODUCTOR', 'TECNICO'] },
  { id: 'seguimiento', label: 'Seguimiento', Icon: IconActivity, roles: ['PRODUCTOR', 'TECNICO'] },
  { id: 'revision', label: 'Revisión técnica', Icon: IconShield, roles: ['TECNICO'] },
  { id: 'conocimiento', label: 'Base de Conocimiento', Icon: IconBook },
  { id: 'adquisicion', label: 'Adquisición', Icon: IconTrending, roles: ['INGENIERO_CONOCIMIENTO'] },
  { id: 'configuracion', label: 'Configuración', Icon: IconSettings },
]
const FANTASMAS = ['60%', '75%', '55%', '68%', '50%']

export default function Sidebar({ activeView, onNavigate, collapsed, onToggle, roles, cargando }: SidebarProps) {
  const visibles = NAV_ITEMS.filter(item => !item.roles || item.roles.some(r => roles.includes(r)))
  return (
    <div className="sidebar" style={{ width: collapsed ? 64 : 240 }}>
      <div className="sidebar-brand">
        <div className="brand-mark"><IconPin size={18} /></div>
        {!collapsed && <div><p>POSCOSEGRAN</p><p>Gestión poscosecha</p></div>}
      </div>

      <nav aria-label="Principal" aria-busy={cargando || undefined}>
        {cargando
          ? FANTASMAS.map((ancho, i) => <div className="sidebar-skeleton" key={i}><Skeleton width={18} height={18} style={{ borderRadius: 5 }} />{!collapsed && <Skeleton width={ancho} height={12} />}</div>)
          : visibles.map(({ id, label, Icon }) => (
            <button key={id} onClick={() => onNavigate(id)} title={collapsed ? label : undefined} aria-label={collapsed ? label : undefined} aria-current={activeView === id ? 'page' : undefined}>
              <Icon size={18} className="flex-shrink-0" />
              {!collapsed && <span>{label}</span>}
            </button>
          ))}
      </nav>

      {!collapsed && <div className="sidebar-foot">Sistema difuso Mamdani · Prototipo académico</div>}

      <button className="sidebar-toggle" onClick={onToggle} aria-label={collapsed ? 'Expandir menú' : 'Colapsar menú'} aria-expanded={!collapsed} title={collapsed ? 'Expandir menú' : 'Colapsar menú'}>
        {collapsed ? <IconChevronRight size={16} /> : <IconChevronLeft size={16} />}
      </button>
    </div>
  )
}
