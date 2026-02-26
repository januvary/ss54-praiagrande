/**
 * Admin Calendar JavaScript
 * Handles calendar rendering, navigation, and day detail drawer
 */

(function () {
    'use strict';

    const monthNames = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ];

    let currentDate = new Date();
    let eventsCache = {};
    let openDrawerDate = null;

    function formatDateKey(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function formatDisplayDate(dateStr) {
        const [year, month, day] = dateStr.split('-');
        return `${day}/${month}/${year}`;
    }

    async function fetchEvents(year, month) {
        const monthKey = `${year}-${String(month + 1).padStart(2, '0')}`;
        
        if (eventsCache[monthKey]) {
            return eventsCache[monthKey];
        }

        try {
            const response = await fetch(`/admin/calendar/events?month=${monthKey}`);
            if (!response.ok) throw new Error('Failed to fetch events');
            
            const data = await response.json();
            const eventMap = {};
            
            for (const event of data.events) {
                eventMap[event.date] = event;
            }
            
            eventsCache[monthKey] = eventMap;
            return eventMap;
        } catch (error) {
            console.error('Error fetching calendar events:', error);
            return {};
        }
    }

    function getEventPriority(event) {
        const priorities = {
            'expiry': 4,
            'deadline_60': 3,
            'deadline_30': 2,
            'batch_sent': 1
        };
        return priorities[event.type] || 0;
    }

    function renderCalendar(events) {
        const grid = document.getElementById('calendar-grid');
        grid.innerHTML = '';

        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        const startPadding = firstDay.getDay();
        const totalDays = lastDay.getDate();

        document.getElementById('current-month-label').textContent = 
            `${monthNames[month]} ${year}`;

        for (let i = 0; i < startPadding; i++) {
            const emptyCell = document.createElement('div');
            emptyCell.className = 'min-h-[100px] border-b border-r border-slate-100 bg-slate-50';
            grid.appendChild(emptyCell);
        }

        for (let day = 1; day <= totalDays; day++) {
            const cell = document.createElement('div');
            const dateKey = formatDateKey(new Date(year, month, day));
            const event = events[dateKey];
            const isToday = today.getFullYear() === year && 
                           today.getMonth() === month && 
                           today.getDate() === day;

            cell.className = `min-h-[100px] border-b border-r border-slate-100 p-2 cursor-pointer hover:bg-slate-50 ${isToday ? 'bg-blue-50' : ''}`;
            cell.dataset.date = dateKey;

            let eventDots = '';
            if (event) {
                const processTypes = new Set(event.processes.map(p => p.type));
                const dots = [];
                let hasEvents = false;
                
                if (event.processes.some(p => p.type === 'sent')) {
                    dots.push('<span class="w-4 h-4 rounded-full bg-blue-500"></span>');
                    hasEvents = true;
                }
                if (event.processes.some(p => p.type === 'predicted')) {
                    dots.push('<span class="w-4 h-4 rounded-full border-2 border-blue-400 bg-white"></span>');
                    hasEvents = true;
                }
                if (event.processes.some(p => p.type === 'drs_30')) {
                    dots.push('<span class="w-4 h-4 rounded-full bg-amber-500"></span>');
                    hasEvents = true;
                }
                if (event.processes.some(p => p.type === 'drs_60')) {
                    dots.push('<span class="w-4 h-4 rounded-full bg-orange-500"></span>');
                    hasEvents = true;
                }
                if (event.processes.some(p => p.type === 'auth_expiry')) {
                    dots.push('<span class="w-4 h-4 rounded-full bg-red-500"></span>');
                    hasEvents = true;
                }
                
                if (hasEvents) {
                    eventDots = `
                        <div class="flex items-center gap-1.5 mt-1 flex-wrap">
                            ${dots.join('')}
                        </div>
                    `;
                }
            }

            cell.innerHTML = `
                <div class="flex flex-col h-full">
                    <span class="text-sm font-medium ${isToday ? 'text-blue-600' : 'text-slate-700'}">${day}</span>
                    ${eventDots}
                </div>
            `;

            cell.addEventListener('click', () => openDrawer(dateKey, event));
            grid.appendChild(cell);
        }

        const remainingCells = (7 - ((startPadding + totalDays) % 7)) % 7;
        for (let i = 0; i < remainingCells; i++) {
            const emptyCell = document.createElement('div');
            emptyCell.className = 'min-h-[100px] border-b border-r border-slate-100 bg-slate-50';
            grid.appendChild(emptyCell);
        }
    }

    function openDrawer(dateKey, event) {
        const drawer = document.getElementById('day-drawer');
        const overlay = document.getElementById('drawer-overlay');
        const drawerDate = document.getElementById('drawer-date');
        const drawerContent = document.getElementById('drawer-content');

        drawerDate.textContent = formatDisplayDate(dateKey);

        if (!event || event.processes.length === 0) {
            drawerContent.innerHTML = `
                <div class="text-center py-8 text-slate-500">
                    <svg class="w-12 h-12 mx-auto text-slate-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                    </svg>
                    <p>Nenhum evento neste dia</p>
                </div>
            `;
        } else {
            const processGroups = {
                sent: [],
                predicted: [],
                drs_30: [],
                drs_60: [],
                auth_expiry: []
            };

            event.processes.forEach(p => {
                if (processGroups[p.type]) {
                    processGroups[p.type].push(p);
                }
            });

            let html = '';

            if (processGroups.predicted.length > 0) {
                html += `
                    <div class="mb-4">
                        <h3 class="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                            <span class="w-4 h-4 rounded-full border-2 border-blue-400 bg-white"></span>
                            Remessa Prevista
                        </h3>
                        <div class="p-4 rounded-lg bg-blue-50 border border-blue-200">
                            <p class="text-sm text-blue-800">
                                Data prevista para próximo envio de lote ao DRS.
                            </p>
                            <p class="text-xs text-blue-600 mt-2">
                                Processos com status "Completo" serão enviados nesta data.
                            </p>
                        </div>
                    </div>
                `;
            }

            if (processGroups.sent.length > 0) {
                html += `
                    <div class="mb-4">
                        <h3 class="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                            <span class="w-4 h-4 rounded-full bg-blue-500"></span>
                            Remessa Enviada (${processGroups.sent.length})
                        </h3>
                        <div class="space-y-2">
                            ${processGroups.sent.map(p => `
                                <a href="/admin/processes/${p.id}" class="block p-3 rounded-lg bg-blue-50 hover:bg-blue-100 transition-colors">
                                    <div class="font-medium text-slate-900">${p.patient_name || 'Paciente'}</div>
                                    <div class="text-sm text-slate-600">${p.protocol}</div>
                                    <div class="text-xs text-slate-500 mt-1">${p.days_ago} dias atrás</div>
                                </a>
                            `).join('')}
                        </div>
                    </div>
                `;
            }

            if (processGroups.drs_30.length > 0) {
                html += `
                    <div class="mb-4">
                        <h3 class="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                            <span class="w-4 h-4 rounded-full bg-amber-500"></span>
                            Prazo 30 Dias DRS (${processGroups.drs_30.length})
                        </h3>
                        <div class="space-y-2">
                            ${processGroups.drs_30.map(p => `
                                <a href="/admin/processes/${p.id}" class="block p-3 rounded-lg bg-amber-50 hover:bg-amber-100 transition-colors">
                                    <div class="font-medium text-slate-900">${p.patient_name || 'Paciente'}</div>
                                    <div class="text-sm text-slate-600">${p.protocol}</div>
                                    <div class="text-xs text-amber-700 mt-1">${p.days_since_sent} dias desde envio</div>
                                </a>
                            `).join('')}
                        </div>
                    </div>
                `;
            }

            if (processGroups.drs_60.length > 0) {
                html += `
                    <div class="mb-4">
                        <h3 class="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                            <span class="w-4 h-4 rounded-full bg-orange-500"></span>
                            Prazo 60 Dias DRS (${processGroups.drs_60.length})
                        </h3>
                        <div class="space-y-2">
                            ${processGroups.drs_60.map(p => `
                                <a href="/admin/processes/${p.id}" class="block p-3 rounded-lg bg-orange-50 hover:bg-orange-100 transition-colors">
                                    <div class="font-medium text-slate-900">${p.patient_name || 'Paciente'}</div>
                                    <div class="text-sm text-slate-600">${p.protocol}</div>
                                    <div class="text-xs text-orange-700 mt-1">${p.days_since_sent} dias desde envio</div>
                                </a>
                            `).join('')}
                        </div>
                    </div>
                `;
            }

            if (processGroups.auth_expiry.length > 0) {
                html += `
                    <div class="mb-4">
                        <h3 class="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                            <span class="w-4 h-4 rounded-full bg-red-500"></span>
                            Expiração Autorização (${processGroups.auth_expiry.length})
                        </h3>
                        <div class="space-y-2">
                            ${processGroups.auth_expiry.map(p => `
                                <a href="/admin/processes/${p.id}" class="block p-3 rounded-lg bg-red-50 hover:bg-red-100 transition-colors">
                                    <div class="font-medium text-slate-900">${p.patient_name || 'Paciente'}</div>
                                    <div class="text-sm text-slate-600">${p.protocol}</div>
                                    <div class="text-xs text-red-700 mt-1">Expira hoje (180 dias)</div>
                                </a>
                            `).join('')}
                        </div>
                    </div>
                `;
            }

            drawerContent.innerHTML = html;
        }

        drawer.classList.remove('translate-x-full');
        overlay.classList.remove('hidden');
        openDrawerDate = dateKey;
    }

    function closeDrawer() {
        const drawer = document.getElementById('day-drawer');
        const overlay = document.getElementById('drawer-overlay');
        
        drawer.classList.add('translate-x-full');
        overlay.classList.add('hidden');
        openDrawerDate = null;
    }

    async function loadMonth() {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        const events = await fetchEvents(year, month);
        renderCalendar(events);
    }

    function init() {
        document.getElementById('prev-month').addEventListener('click', () => {
            currentDate.setMonth(currentDate.getMonth() - 1);
            loadMonth();
        });

        document.getElementById('next-month').addEventListener('click', () => {
            currentDate.setMonth(currentDate.getMonth() + 1);
            loadMonth();
        });

        document.getElementById('today-btn').addEventListener('click', () => {
            currentDate = new Date();
            loadMonth();
        });

        document.getElementById('close-drawer').addEventListener('click', closeDrawer);
        document.getElementById('drawer-overlay').addEventListener('click', closeDrawer);

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && openDrawerDate) {
                closeDrawer();
            }
        });

        loadMonth();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
