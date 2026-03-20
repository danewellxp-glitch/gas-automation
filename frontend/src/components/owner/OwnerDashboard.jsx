/**
 * Owner Dashboard - Dashboard Executivo com Navegação Lateral
 * 
 * Estrutura profissional com seções separadas:
 * - Dashboard (Visão Geral)
 * - Financeiro (Breakdown completo)
 * - Operação (Gráficos e análises)
 * - Performance (Entregadores e operadores)
 * - Clientes (Clientes & Mercado)
 * - Relatórios (Exportáveis)
 * - Configurações (De Negócio)
 */

import { useState } from 'react'
import {
  LayoutDashboard, DollarSign, Package, TrendingUp, Users,
  FileText, Settings, MessageSquare
} from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import FlowbiteLayout from '../../components/flowbite/FlowbiteLayout'
import BusinessStatusWidget from '../../components/owner/BusinessStatusWidget'
import DashboardOverview from '../../components/owner/DashboardOverview'
import FinancialView from '../../components/owner/FinancialView'
import OperationalView from '../../components/owner/OperationalView'
import PerformanceView from '../../components/owner/PerformanceView'
import CustomersView from '../../components/owner/CustomersView'
import OwnerReportsView from '../../components/owner/OwnerReportsView'
import OwnerSettingsView from '../../components/owner/OwnerSettingsView'
import WhatsAppBroadcast from '../../components/WhatsAppBroadcast'

export default function OwnerDashboard() {
  const { user, logout } = useAuth()
  const [activeView, setActiveView] = useState('dashboard')

  return (
    <FlowbiteLayout
      appName="Gas Automation"
      pageTitle="Dashboard Executivo"
      userEmail={user?.email || ''}
      onLogout={logout}
      rightSlot={<BusinessStatusWidget />}
      activeNavKey={activeView}
      navItems={[
        { 
          key: 'dashboard', 
          type: 'button', 
          label: 'Dashboard', 
          icon: LayoutDashboard, 
          onClick: () => setActiveView('dashboard') 
        },
        { 
          key: 'financial', 
          type: 'button', 
          label: 'Financeiro', 
          icon: DollarSign, 
          onClick: () => setActiveView('financial') 
        },
        { 
          key: 'operational', 
          type: 'button', 
          label: 'Operação', 
          icon: Package, 
          onClick: () => setActiveView('operational') 
        },
        { 
          key: 'performance', 
          type: 'button', 
          label: 'Performance', 
          icon: TrendingUp, 
          onClick: () => setActiveView('performance') 
        },
        { 
          key: 'customers', 
          type: 'button', 
          label: 'Clientes', 
          icon: Users, 
          onClick: () => setActiveView('customers') 
        },
        { 
          key: 'reports', 
          type: 'button', 
          label: 'Relatórios', 
          icon: FileText, 
          onClick: () => setActiveView('reports') 
        },
        { 
          key: 'whatsapp-broadcast', 
          type: 'button', 
          label: 'Disparo WhatsApp', 
          icon: MessageSquare, 
          onClick: () => setActiveView('whatsapp-broadcast') 
        },
        { 
          key: 'settings', 
          type: 'button', 
          label: 'Configurações', 
          icon: Settings, 
          onClick: () => setActiveView('settings') 
        },
      ]}
    >
      {/* Renderizar view baseada no estado */}
      {activeView === 'dashboard' && <DashboardOverview />}
      {activeView === 'financial' && <FinancialView />}
      {activeView === 'operational' && <OperationalView />}
      {activeView === 'performance' && <PerformanceView />}
      {activeView === 'customers' && <CustomersView />}
      {activeView === 'reports' && <OwnerReportsView />}
      {activeView === 'settings' && <OwnerSettingsView />}
      {activeView === 'whatsapp-broadcast' && <WhatsAppBroadcast />}
    </FlowbiteLayout>
  )
}
