import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  BarChart3, 
  TrendingUp, 
  Users, 
  Activity, 
  ArrowRight, 
  ArrowUpRight, 
  Clock, 
  ChevronRight,
  Microscope,
  Eye,
  Footprints,
  Droplet,
  ScanLine
} from 'lucide-react';
import { 
  PieChart, 
  Pie, 
  Cell, 
  ResponsiveContainer, 
  Legend, 
  Tooltip,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid
} from 'recharts';
import { predictionsAPI } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import s from './DashboardPage.module.css';

const DashboardPage = () => {
    const { user } = useAuth();
    const { t } = useTranslation();
    const [stats, setStats] = useState({
        total: 0,
        anemic: 0,
        diabetic: 0,
        dfu: 0,
        healthy: 0,
        recent: [],
        trends: [],
        risks: { anemia: 'low', diabetes: 'low' }
    });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchDashboardData = async () => {
            try {
                // Fetch stats for accurate totals and trends, and history only for recent activity
                const [statsRes, historyRes] = await Promise.all([
                    predictionsAPI.getStats(),
                    predictionsAPI.getHistory(1, 10)
                ]);
                
                const statsData = statsRes.data;
                const history = historyRes.data.predictions || [];
                
                // Authoritative Mutual Exclusivity: Group by Primary Focus
                const anemiaCount = history.filter(p => p.primary_diagnosis === 'Anemia' && p.primary_status === 'Anemic').length;
                const diabetesCount = history.filter(p => p.primary_diagnosis === 'Diabetes' && p.primary_status === 'Diabetic').length;
                const dfuCount = history.filter(p => p.primary_diagnosis === 'Diabetes' && p.primary_status === 'Abnormal(Ulcer)').length;

                // Trend Analysis: Group by Day (Last 7 days)
                const trendMap = history.reduce((acc, scan) => {
                    const date = new Date(scan.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                    if (!acc[date]) acc[date] = { date, Anemia: 0, Diabetes: 0 };
                    
                    if (scan.primary_diagnosis === 'Anemia' && scan.primary_status === 'Anemic') acc[date].Anemia++;
                    if (scan.primary_diagnosis === 'Diabetes' && (scan.primary_status === 'Diabetic' || scan.primary_status === 'Abnormal(Ulcer)')) acc[date].Diabetes++;
                    
                    return acc;
                }, {});

                const trendData = Object.values(trendMap).sort((a, b) => new Date(a.date) - new Date(b.date)).slice(-7);

                // Risk Profile Analysis: Last 10 Scans
                const last10 = history.slice(0, 10);
                const aCount10 = last10.filter(p => p.primary_diagnosis === 'Anemia' && p.primary_status === 'Anemic').length;
                const dCount10 = last10.filter(p => p.primary_diagnosis === 'Diabetes' && (p.primary_status === 'Diabetic' || p.primary_status === 'Abnormal(Ulcer)')).length;

                const getRiskStatus = (count) => {
                    if (count > 3) return 'high';
                    if (count > 0) return 'medium';
                    return 'low';
                };

                setStats({
                    total: statsData.total_scans,
                    anemic: statsData.anemia_detected,
                    diabetic: statsData.diabetes_detected,
                    dfu: statsData.dfu_detected,
                    healthy: statsData.healthy_cases,
                    recent: history.slice(0, 3),
                    trends: statsData.trends || [],
                    risks: {
                        anemia: getRiskStatus(aCount10),
                        diabetes: getRiskStatus(dCount10)
                    }
                });
            } catch (err) {
                console.error("Dashboard metric sync failed", err);
            } finally {
                setLoading(false);
            }
        };

        fetchDashboardData();
    }, []);

    const chartData = [
        { name: 'Anemia', value: stats.anemic, color: '#dc2626' },
        { name: 'Diabetes', value: stats.diabetic, color: '#059669' },
        { name: 'DFU', value: stats.dfu, color: '#d97706' },
        { name: 'Healthy', value: Math.max(0, stats.total - (stats.anemic + stats.diabetic + stats.dfu)), color: '#1a56db' }
    ].filter(d => d.value > 0);

    const statCards = [
        { label: t('dashboard.total_scans'), value: stats.total, icon: <Microscope size={26} />, bg: '#eff6ff', color: '#1a56db' },
        { label: t('dashboard.anemia_cases'), value: stats.anemic, icon: <Droplet size={26} />, bg: '#fef2f2', color: '#dc2626' },
        { label: t('dashboard.diabetes_signs'), value: stats.diabetic, icon: <Eye size={26} />, bg: '#f0fdf4', color: '#059669' },
        { label: t('dashboard.healthy_cases'), value: stats.healthy, icon: <Activity size={26} />, bg: '#eff6ff', color: '#1a56db' },
    ];

    if (loading) return (
        <div style={{ padding: '80px', textAlign: 'center' }}>
            <Activity className="animate-spin" size={60} color="#1a56db" />
            <p style={{ marginTop: '24px', color: '#64748b', fontSize: '20px', fontWeight: 600, fontFamily: "'DM Sans', sans-serif" }}>{t('dashboard.syncing')}</p>
        </div>
    );

    return (
        <div className={s.page} style={{ 
            width: '100%', margin: '0 auto', padding: '48px 5vw',
            animation: 'fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1)'
        }}>
            {/* Header Section */}
            <div style={{ marginBottom: '52px' }}>
                <h1 style={{ 
                    fontSize: '56px', fontWeight: 900, color: '#111827', 
                    fontFamily: "'Outfit', sans-serif", marginBottom: '12px',
                    letterSpacing: '-2px'
                }}>
                    {t('dashboard.welcome_back')}, {user?.name?.split(' ')[0]}
                </h1>
                <p style={{ fontSize: '24px', color: '#64748b', fontFamily: "'DM Sans', sans-serif", fontWeight: 500 }}>
                    {t('dashboard.subtitle')}
                </p>
            </div>

            {/* Stat Cards Grid */}
            <div className={s.statsGrid} style={{ 
                display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', 
                gap: '24px', marginBottom: '40px' 
            }}>
                {statCards.map((card, idx) => (
                    <div key={idx} style={{
                        background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '32px',
                        padding: '48px 40px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.02)',
                        minHeight: '220px', display: 'flex', flexDirection: 'column',
                        transition: 'transform 0.3s ease, box-shadow 0.3s ease',
                        cursor: 'default'
                    }} className="hover-lift">
                        <div style={{
                            width: '72px', height: '72px', borderRadius: '22px',
                            background: card.bg, color: card.color,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            boxShadow: `0 8px 16px ${card.bg}`
                        }}>
                            {React.cloneElement(card.icon, { size: 36 })}
                        </div>
                        <div style={{ 
                            fontSize: '18px', fontWeight: 900, color: '#94a3b8', 
                            textTransform: 'uppercase', letterSpacing: '1.5px',
                            marginTop: '32px', marginBottom: '16px',
                            fontFamily: "'DM Sans', sans-serif"
                        }}>
                            {card.label}
                        </div>
                        <div style={{ 
                            fontSize: '64px', fontWeight: 900, color: '#111827', 
                            fontFamily: "'Outfit', sans-serif", lineHeight: 1,
                            letterSpacing: '-3px'
                        }}>
                            {card.value}
                        </div>
                    </div>
                ))}
            </div>

            {/* Main Content Sections */}
            <div className={s.mainGrid} style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '32px' }}>
                
                {/* Detection Overview */}
                <div style={{ 
                    background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '32px',
                    padding: '48px', minHeight: '520px', display: 'flex', flexDirection: 'column',
                    boxShadow: '0 4px 6px -1px rgba(0,0,0,0.02)'
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '40px' }}>
                        <h2 style={{ fontSize: '40px', fontWeight: 900, color: '#111827', fontFamily: "'Outfit', sans-serif", letterSpacing: '-1.5px' }}>{t('dashboard.detection_overview')}</h2>
                        <div style={{ display: 'flex', gap: '8px' }}>
                             <button style={{ 
                                 padding: '10px 20px', borderRadius: '12px', background: '#fff', border: '1px solid #e2e8f0', 
                                 fontSize: '16px', fontWeight: 800, color: '#374151', cursor: 'pointer', fontFamily: "'DM Sans', sans-serif"
                             }}>{t('dashboard.weekly')}</button>
                             <button style={{ 
                                 padding: '10px 20px', borderRadius: '12px', background: '#eff6ff', border: '1px solid #bfdbfe', 
                                 fontSize: '16px', fontWeight: 800, color: '#1a56db', cursor: 'pointer', fontFamily: "'DM Sans', sans-serif"
                             }}>{t('dashboard.monthly')}</button>
                        </div>
                    </div>
                    
                    {stats.total > 0 ? (
                        <div style={{ flex: 1 }}>
                            <ResponsiveContainer width="100%" height={360}>
                                <PieChart>
                                    <Pie
                                        data={chartData}
                                        innerRadius={90}
                                        outerRadius={130}
                                        paddingAngle={8}
                                        dataKey="value"
                                        stroke="none"
                                    >
                                        {chartData.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={entry.color} />
                                        ))}
                                    </Pie>
                                    <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px rgba(0,0,0,0.1)' }} />
                                    <Legend verticalAlign="bottom" height={48} iconType="circle" />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                    ) : (
                        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px', textAlign: 'center' }}>
                            <Activity size={48} color="#94a3b8" style={{ marginBottom: '20px', opacity: 0.5 }} />
                            <div style={{ fontSize: '18px', fontWeight: 700, color: '#111827', fontFamily: "'Outfit', sans-serif", marginBottom: '8px' }}>No scan data yet</div>
                            <p style={{ fontSize: '14px', color: '#6b7280', fontFamily: "'DM Sans', sans-serif", fontWeight: 400, maxWidth: '280px', margin: '0 auto' }}>
                                Run your first scan to see results here.
                            </p>
                        </div>
                    )}
                </div>

                {/* Quick Actions & Recent */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                    
                    <Link to="/scan" style={{
                        background: 'linear-gradient(135deg, #1a56db, #2563eb)',
                        borderRadius: '32px', padding: '56px 48px', cursor: 'pointer',
                        textDecoration: 'none', display: 'flex', justifyContent: 'space-between',
                        alignItems: 'center', boxShadow: '0 12px 30px rgba(26,86,219,0.2)'
                    }}>
                        <div style={{ display: 'flex', gap: '32px', alignItems: 'center' }}>
                            <div style={{ 
                                width: '84px', height: '84px', background: 'rgba(255,255,255,0.15)',
                                borderRadius: '28px', display: 'flex', alignItems: 'center', justifyContent: 'center'
                            }}>
                                <ScanLine size={48} color="#fff" />
                            </div>
                            <div>
                                <div style={{ color: '#fff', fontWeight: 900, fontSize: '42px', fontFamily: "'Outfit', sans-serif", letterSpacing: '-1px' }}>{t('dashboard.start_new_scan')}</div>
                                <div style={{ color: 'rgba(255,255,255,0.85)', fontSize: '22px', fontWeight: 600, fontFamily: "'DM Sans', sans-serif", marginTop: '4px' }}>{t('dashboard.upload_desc')}</div>
                            </div>
                        </div>
                        <ArrowRight color="#fff" size={48} />
                    </Link>

                    <div style={{ 
                        background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '32px',
                        padding: '40px', flex: 1, boxShadow: '0 4px 6px -1px rgba(0,0,0,0.02)'
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
                            <h3 style={{ fontSize: '40px', fontWeight: 900, color: '#111827', fontFamily: "'Outfit', sans-serif", letterSpacing: '-1.5px' }}>{t('dashboard.recent_activity')}</h3>
                            <Link to="/history" style={{ fontSize: '22px', fontWeight: 900, color: '#1a56db', textDecoration: 'none', fontFamily: "'DM Sans', sans-serif" }}>{t('dashboard.expand_all')}</Link>
                        </div>

                        {stats.recent.length > 0 ? (
                            <div style={{ display: 'flex', flexDirection: 'column' }}>
                                {stats.recent.map((scan, idx) => (
                                    <Link key={idx} to={`/results/${scan.id}`} style={{
                                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                        padding: '24px 0', borderBottom: idx < stats.recent.length - 1 ? '1px solid #f1f5f9' : 'none',
                                        textDecoration: 'none', transition: 'all 0.2s'
                                    }} className="recent-item">
                                        <div>
                                            <div style={{ fontSize: '21px', color: '#94a3b8', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '10px', fontWeight: 800 }}>
                                                <Clock size={22} /> {new Date(scan.created_at).toLocaleDateString()}
                                            </div>
                                            <div style={{ display: 'flex', gap: '12px' }}>
                                                <div style={{ 
                                                    fontSize: '18px', fontWeight: 900, padding: '8px 18px', 
                                                    borderRadius: '12px', background: '#f1f5f9', color: '#475569',
                                                    fontFamily: "'DM Sans', sans-serif"
                                                }}>ID: {String(scan.id).slice(0, 8)}</div>
                                            </div>
                                        </div>
                                        <div style={{
                                            padding: '12px 24px', borderRadius: '14px', fontSize: '21px', fontWeight: 1000,
                                            background: scan.overall_risk === 'high' ? '#fef2f2' : (scan.overall_risk === 'medium' ? '#fff7ed' : '#f0fdf4'),
                                            color: scan.overall_risk === 'high' ? '#dc2626' : (scan.overall_risk === 'medium' ? '#d97706' : '#059669'),
                                            textTransform: 'uppercase', letterSpacing: '1px',
                                            fontFamily: "'DM Sans', sans-serif"
                                        }}>
                                            {scan.overall_risk} {t('dashboard.risk')}
                                        </div>
                                    </Link>
                                ))}
                            </div>
                        ) : (
                            <div style={{ textAlign: 'center', padding: '60px 0', color: '#94a3b8', fontSize: '15px', fontWeight: 500 }}>
                                No recent clinical data found.
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Clinical Risk Profile */}
            <div style={{ 
                background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '32px',
                padding: '48px', marginBottom: '40px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.02)'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '40px' }}>
                    <div>
                        <h2 style={{ fontSize: '40px', fontWeight: 900, color: '#111827', fontFamily: "'Outfit', sans-serif", letterSpacing: '-1.5px', marginBottom: '8px' }}>{t('dashboard.risk_profile')}</h2>
                        <p style={{ fontSize: '18px', color: '#64748b', fontFamily: "'DM Sans', sans-serif" }}>{t('dashboard.based_on_scans')}</p>
                    </div>
                </div>

                <div className={s.riskProfileGrid} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px' }}>
                    {['anemia', 'diabetes'].map((type) => (
                        <div key={type} style={{
                            padding: '32px', borderRadius: '24px', background: '#f8fafc',
                            border: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', justifyContent: 'space-between'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                                <div style={{ 
                                    width: '64px', height: '64px', borderRadius: '20px',
                                    background: type === 'anemia' ? '#fef2f2' : '#f0fdf4',
                                    color: type === 'anemia' ? '#dc2626' : '#059669',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                                }}>
                                    {type === 'anemia' ? <Droplet size={32} /> : <Eye size={32} />}
                                </div>
                                <div style={{ fontSize: '24px', fontWeight: 800, color: '#1e293b', fontFamily: "'Outfit', sans-serif" }}>
                                    {type === 'anemia' ? t('dashboard.anemia_risk') : t('dashboard.diabetes_risk')}
                                </div>
                            </div>

                            <div style={{
                                padding: '12px 24px', borderRadius: '16px', fontSize: '20px', fontWeight: 900,
                                background: stats.risks[type] === 'high' ? '#fef2f2' : (stats.risks[type] === 'medium' ? '#fff7ed' : '#f0fdf4'),
                                color: stats.risks[type] === 'high' ? '#dc2626' : (stats.risks[type] === 'medium' ? '#d97706' : '#059669'),
                                letterSpacing: '1px'
                            }}>
                                {t(`dashboard.risk_${stats.risks[type]}`)}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Diagnostic Trends (Full Width) */}
            {stats.trends.length > 0 && (
                <div style={{ 
                    background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '32px',
                    padding: '48px', minHeight: '520px', display: 'flex', flexDirection: 'column',
                    boxShadow: '0 4px 6px -1px rgba(0,0,0,0.02)', marginTop: '40px'
                }}>
                    <h2 style={{ fontSize: '40px', fontWeight: 900, color: '#111827', fontFamily: "'Outfit', sans-serif", letterSpacing: '-1.5px', marginBottom: '40px' }}>{t('dashboard.diagnostic_trends')}</h2>
                    
                    <div style={{ flex: 1 }}>
                        <ResponsiveContainer width="100%" height={380}>
                            <LineChart data={stats.trends}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                <XAxis 
                                    dataKey="date" 
                                    axisLine={false} 
                                    tickLine={false} 
                                    tick={{ fill: '#94a3b8', fontSize: 14, fontWeight: 600 }}
                                    dy={10}
                                />
                                <YAxis 
                                    axisLine={false} 
                                    tickLine={false} 
                                    tick={{ fill: '#94a3b8', fontSize: 14, fontWeight: 600 }}
                                />
                                <Tooltip 
                                    contentStyle={{ borderRadius: '16px', border: 'none', boxShadow: '0 10px 25px rgba(0,0,0,0.1)', padding: '16px' }}
                                    itemStyle={{ fontWeight: 800 }}
                                />
                                <Legend verticalAlign="top" align="right" iconType="circle" wrapperStyle={{ paddingBottom: '20px' }} />
                                <Line 
                                    type="monotone" 
                                    dataKey="Anemia" 
                                    stroke="#dc2626" 
                                    strokeWidth={4} 
                                    dot={{ r: 6, fill: '#dc2626', strokeWidth: 2, stroke: '#fff' }}
                                    activeDot={{ r: 8 }}
                                />
                                <Line 
                                    type="monotone" 
                                    dataKey="Diabetes" 
                                    stroke="#059669" 
                                    strokeWidth={4} 
                                    dot={{ r: 6, fill: '#059669', strokeWidth: 2, stroke: '#fff' }}
                                    activeDot={{ r: 8 }}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            )}

            <style>{`
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(15px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .hover-lift:hover {
                    transform: translateY(-8px);
                    box-shadow: 0 20px 25px -5px rgba(0,0,0,0.05);
                    border-color: #bfdbfe !important;
                }
                .recent-item:hover {
                    padding-left: 8px !important;
                    background: #f8fafc;
                    border-radius: 12px;
                }
            `}</style>
        </div>
    );
};

export default DashboardPage;
