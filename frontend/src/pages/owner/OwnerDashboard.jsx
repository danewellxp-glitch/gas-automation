/**
 * Owner Dashboard — Painel Executivo Completo
 *
 * Nav structure:
 * - Dashboard
 * - Financeiro (11 sub-menus)
 * - Operação (7 sub-menus)
 * - Performance
 * - Clientes
 * - Relatórios (5 sub-menus)
 * - Disparo WhatsApp
 * - Configurações
 */

import { useState } from 'react'
import {
  LayoutDashboard, DollarSign, Package, TrendingUp, Users,
  FileText, Settings, MessageSquare, QrCode, Receipt,
  List, ArrowDownCircle, ArrowUpCircle, CreditCard, Landmark,
  FileCheck, ShoppingCart, Clock, CalendarDays, Map, Wifi,
  MessageCircle, BarChart2, RefreshCw, Activity,
} from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import FlowbiteLayout from '../../components/flowbite/FlowbiteLayout'
import BusinessStatusWidget from '../../components/owner/BusinessStatusWidget'

// ── Views existentes ─────────────────────────────────────────────────────────
import DashboardOverview   from '../../components/owner/DashboardOverview'
import FinancialView       from '../../components/owner/FinancialView'
import OperationalView     from '../../components/owner/OperationalView'
import PerformanceView     from '../../components/owner/PerformanceView'
import CustomersView       from '../../components/owner/CustomersView'
import OwnerSettingsView   from '../../components/owner/OwnerSettingsView'
import WhatsAppBroadcast   from '../../components/WhatsAppBroadcast'
import PIXAsaasPanel       from '../../components/operator/PIXAsaasPanel'
import DespesasPanel       from '../../components/operator/DespesasPanel'

// ── Novos sub-menus Financeiro ───────────────────────────────────────────────
import FinLancamentos      from '../../components/owner/FinLancamentos'
import FinPIX              from '../../components/owner/FinPIX'
import FinAReceber         from '../../components/owner/FinAReceber'
import FinAPagar           from '../../components/owner/FinAPagar'
import FinFiado            from '../../components/owner/FinFiado'
import FinLucratividade    from '../../components/owner/FinLucratividade'
import FinContas           from '../../components/owner/FinContas'
import FinNFe              from '../../components/owner/FinNFe'

// ── Novos sub-menus Operação ─────────────────────────────────────────────────
import OpPedidos           from '../../components/owner/OpPedidos'
import OpPendentes         from '../../components/owner/OpPendentes'
import OpAgendados         from '../../components/owner/OpAgendados'
import OpMapa              from '../../components/owner/OpMapa'
import OpOnline            from '../../components/owner/OpOnline'
import OpConversas         from '../../components/owner/OpConversas'

// ── Novos sub-menus Relatórios ───────────────────────────────────────────────
import RelFaturamento      from '../../components/owner/RelFaturamento'
import RelPedidos          from '../../components/owner/RelPedidos'
import RelDesempenho       from '../../components/owner/RelDesempenho'
import RelPIX              from '../../components/owner/RelPIX'
import RelDespesas         from '../../components/owner/RelDespesas'

export default function OwnerDashboard() {
  const { user, logout } = useAuth()
  const [activeView, setActiveView] = useState('dashboard')

  const nav = (view) => () => setActiveView(view)

  const navItems = [
    {
      key: 'dashboard',
      type: 'button',
      label: 'Dashboard',
      icon: LayoutDashboard,
      onClick: nav('dashboard'),
    },

    // ── FINANCEIRO ─────────────────────────────────────────────────────────
    {
      key: 'financial',
      type: 'group',
      label: 'Financeiro',
      icon: DollarSign,
      children: [
        { key: 'fin-visao',         type: 'button', label: 'Visão Geral',       icon: BarChart2,        onClick: nav('fin-visao') },
        { key: 'fin-lancamentos',   type: 'button', label: 'Lançamentos',       icon: List,             onClick: nav('fin-lancamentos') },
        { key: 'fin-despesas',      type: 'button', label: 'Despesas',          icon: Receipt,          onClick: nav('fin-despesas') },
        { key: 'fin-pix',           type: 'button', label: 'PIX',               icon: QrCode,           onClick: nav('fin-pix') },
        { key: 'fin-pix-asaas',     type: 'button', label: 'Conciliação PIX',   icon: RefreshCw,        onClick: nav('fin-pix-asaas') },
        { key: 'fin-areceber',      type: 'button', label: 'A Receber',         icon: ArrowDownCircle,  onClick: nav('fin-areceber') },
        { key: 'fin-apagar',        type: 'button', label: 'A Pagar',           icon: ArrowUpCircle,    onClick: nav('fin-apagar') },
        { key: 'fin-fiado',         type: 'button', label: 'Fiado',             icon: CreditCard,       onClick: nav('fin-fiado') },
        { key: 'fin-lucratividade', type: 'button', label: 'Lucratividade',     icon: TrendingUp,       onClick: nav('fin-lucratividade') },
        { key: 'fin-contas',        type: 'button', label: 'Contas',            icon: Landmark,         onClick: nav('fin-contas') },
        { key: 'fin-nfe',           type: 'button', label: 'NF-e',              icon: FileCheck,        onClick: nav('fin-nfe') },
      ],
    },

    // ── OPERAÇÃO ───────────────────────────────────────────────────────────
    {
      key: 'operational',
      type: 'group',
      label: 'Operação',
      icon: Package,
      children: [
        { key: 'op-dashboard', type: 'button', label: 'Dashboard',         icon: Activity,       onClick: nav('op-dashboard') },
        { key: 'op-pedidos',   type: 'button', label: 'Pedidos',           icon: ShoppingCart,   onClick: nav('op-pedidos') },
        { key: 'op-pendentes', type: 'button', label: 'Pendentes',         icon: Clock,          onClick: nav('op-pendentes') },
        { key: 'op-agendados', type: 'button', label: 'Agendados',         icon: CalendarDays,   onClick: nav('op-agendados') },
        { key: 'op-mapa',      type: 'button', label: 'Mapa',              icon: Map,            onClick: nav('op-mapa') },
        { key: 'op-online',    type: 'button', label: 'Online',            icon: Wifi,           onClick: nav('op-online') },
        { key: 'op-conversas', type: 'button', label: 'Conversas',         icon: MessageCircle,  onClick: nav('op-conversas') },
      ],
    },

    {
      key: 'performance',
      type: 'button',
      label: 'Performance',
      icon: TrendingUp,
      onClick: nav('performance'),
    },
    {
      key: 'customers',
      type: 'button',
      label: 'Clientes',
      icon: Users,
      onClick: nav('customers'),
    },

    // ── RELATÓRIOS ─────────────────────────────────────────────────────────
    {
      key: 'reports',
      type: 'group',
      label: 'Relatórios',
      icon: FileText,
      children: [
        { key: 'rel-faturamento', type: 'button', label: 'Faturamento', icon: DollarSign,   onClick: nav('rel-faturamento') },
        { key: 'rel-pedidos',     type: 'button', label: 'Pedidos',     icon: ShoppingCart, onClick: nav('rel-pedidos') },
        { key: 'rel-desempenho',  type: 'button', label: 'Desempenho',  icon: BarChart2,    onClick: nav('rel-desempenho') },
        { key: 'rel-pix',         type: 'button', label: 'PIX',         icon: QrCode,       onClick: nav('rel-pix') },
        { key: 'rel-despesas',    type: 'button', label: 'Despesas',    icon: Receipt,      onClick: nav('rel-despesas') },
      ],
    },

    {
      key: 'whatsapp-broadcast',
      type: 'button',
      label: 'Disparo WhatsApp',
      icon: MessageSquare,
      onClick: nav('whatsapp-broadcast'),
    },
    {
      key: 'settings',
      type: 'button',
      label: 'Configurações',
      icon: Settings,
      onClick: nav('settings'),
    },
  ]

  const renderView = () => {
    switch (activeView) {
      // ── Dashboard ─────────────────────────────────────────────────────
      case 'dashboard':          return <DashboardOverview />

      // ── Financeiro ────────────────────────────────────────────────────
      case 'fin-visao':          return <FinancialView />
      case 'fin-lancamentos':    return <FinLancamentos />
      case 'fin-despesas':       return <DespesasPanel />
      case 'fin-pix':            return <FinPIX />
      case 'fin-pix-asaas':      return <PIXAsaasPanel />
      case 'fin-areceber':       return <FinAReceber />
      case 'fin-apagar':         return <FinAPagar />
      case 'fin-fiado':          return <FinFiado />
      case 'fin-lucratividade':  return <FinLucratividade />
      case 'fin-contas':         return <FinContas />
      case 'fin-nfe':            return <FinNFe />

      // ── Operação ──────────────────────────────────────────────────────
      case 'op-dashboard':       return <OperationalView />
      case 'op-pedidos':         return <OpPedidos />
      case 'op-pendentes':       return <OpPendentes />
      case 'op-agendados':       return <OpAgendados />
      case 'op-mapa':            return <OpMapa />
      case 'op-online':          return <OpOnline />
      case 'op-conversas':       return <OpConversas />

      // ── Outros ────────────────────────────────────────────────────────
      case 'performance':        return <PerformanceView />
      case 'customers':          return <CustomersView />

      // ── Relatórios ────────────────────────────────────────────────────
      case 'rel-faturamento':    return <RelFaturamento />
      case 'rel-pedidos':        return <RelPedidos />
      case 'rel-desempenho':     return <RelDesempenho />
      case 'rel-pix':            return <RelPIX />
      case 'rel-despesas':       return <RelDespesas />

      // ── Config / WA ───────────────────────────────────────────────────
      case 'settings':           return <OwnerSettingsView />
      case 'whatsapp-broadcast': return <WhatsAppBroadcast />

      default:                   return <DashboardOverview />
    }
  }

  return (
    <FlowbiteLayout
      appName="Gas Automation"
      pageTitle="Dashboard Executivo"
      userEmail={user?.email || ''}
      onLogout={logout}
      rightSlot={<BusinessStatusWidget />}
      activeNavKey={activeView}
      navItems={navItems}
    >
      {renderView()}
    </FlowbiteLayout>
  )
}
