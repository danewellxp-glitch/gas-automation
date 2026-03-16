import { useState, useMemo } from 'react'
import { Flame } from 'lucide-react'

// Mock Data para exemplificar a densidade visual caso a API não provenha dados reais
const generateMockHeatmapData = () => {
    const days = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
    const hours = Array.from({ length: 15 }, (_, i) => i + 8); // 08:00 às 22:00

    const data = [];

    days.forEach(day => {
        hours.forEach(hour => {
            // Cria padrões realistas: Picos no fds e almoço/jantar
            let intensity = Math.random() * 20; // Base: 0 a 20 pedidos

            const isWeekend = day === 'Sáb' || day === 'Dom';
            const isLunch = hour >= 11 && hour <= 13;
            const isDinner = hour >= 18 && hour <= 20;

            if (isWeekend) intensity *= 2;
            if (isLunch || isDinner) intensity *= 2.5;

            data.push({
                day,
                hour: `${hour}:00`,
                value: Math.floor(intensity)
            });
        });
    });

    return { days, hours: hours.map(h => `${h}:00`), data };
}

export default function SalesHeatmap({ data }) {
    // Usa dados da prop ou o mock para visualização
    const heatmapConfig = useMemo(() => {
        // Se data é diretamente um array de objetos {day, hour, value}
        if (Array.isArray(data) && data.length > 0) {
            return {
                days: ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'],
                hours: Array.from({ length: 15 }, (_, i) => `${i + 8}:00`),
                data
            }
        }

        // Se data é un objeto com { days, hours, data }
        if (data && data.data && Array.isArray(data.data) && data.data.length > 0) {
            return data
        }

        // Fallback: mock data para demonstração visual
        return generateMockHeatmapData()
    }, [data])

    const { days, hours, data: heatData } = heatmapConfig;

    const maxValue = heatData && heatData.length > 0 ? Math.max(...heatData.map(d => d.value)) : 1;

    // Função para retornar a cor baseada na intensidade (tons do primary color #667eea)
    const getBackgroundColor = (value) => {
        if (value === 0) return 'rgba(243, 244, 246, 1)'; // gray-100

        // Calcula a porcentagem em relação ao máximo para definir opacidade/intensidade
        const percentage = value / maxValue;

        // Paleta em gradiente do ciano/azul para o roxo/azul-escuro
        if (percentage < 0.2) return 'rgba(199, 210, 254, 0.4)'; // indigo-200 fraco
        if (percentage < 0.4) return 'rgba(165, 180, 252, 0.6)'; // indigo-300
        if (percentage < 0.6) return 'rgba(129, 140, 248, 0.8)'; // indigo-400
        if (percentage < 0.8) return 'rgba(99, 102, 241, 0.9)';  // indigo-500
        return 'rgba(79, 70, 229, 1)'; // indigo-600 max
    };

    const getTextColor = (value) => {
        const percentage = value / maxValue;
        return percentage > 0.6 ? 'text-white' : 'text-transparent group-hover:text-gray-900';
    };

    return (
        <div className="w-full overflow-x-auto">
            <div className="flex items-center gap-2 mb-4">
                <Flame className="h-5 w-5 text-orange-500" />
                <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                    Horários de Pico (Últimos 30 Dias)
                </h3>
            </div>

            <div className="min-w-[600px]">
                {/* Cabecalho de Horas */}
                <div className="flex ml-12 mb-2">
                    {hours.map(hour => (
                        <div key={hour} className="flex-1 text-center text-xs text-gray-500">
                            {hour.split(':')[0]}h
                        </div>
                    ))}
                </div>

                {/* Grid de Dias */}
                <div className="flex flex-col gap-1">
                    {days.map(day => (
                        <div key={day} className="flex items-center h-8">
                            <div className="w-12 text-xs font-medium text-gray-600 pr-2 text-right">
                                {day}
                            </div>
                            <div className="flex flex-1 gap-1">
                                {hours.map(hour => {
                                    const cellData = heatData.find(d => d.day === day && d.hour === hour) || { value: 0 };
                                    const bg = getBackgroundColor(cellData.value);

                                    return (
                                        <div
                                            key={`${day}-${hour}`}
                                            className="group relative flex-1 h-full rounded-sm cursor-pointer transition-transform hover:scale-110 flex items-center justify-center"
                                            style={{ backgroundColor: bg }}
                                        >
                                            {/* Tooltip on hover */}
                                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block z-10">
                                                <div className="bg-gray-900 text-white text-xs py-1 px-2 rounded whitespace-nowrap">
                                                    {day} às {hour}: <span className="font-bold text-indigo-300">{cellData.value} pedidos</span>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Legenda */}
                <div className="flex items-center justify-end gap-2 mt-4 text-xs text-gray-500">
                    <span>Menos pedidos</span>
                    <div className="flex gap-1">
                        {[0, 0.2, 0.4, 0.6, 0.8, 1].map(v => (
                            <div
                                key={v}
                                className="w-4 h-4 rounded-sm"
                                style={{ backgroundColor: getBackgroundColor(maxValue * v) }}
                            />
                        ))}
                    </div>
                    <span>Mais pedidos</span>
                </div>
            </div>
        </div>
    )
}
