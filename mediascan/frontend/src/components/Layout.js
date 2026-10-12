import React, { useState, useEffect, useRef } from 'react';
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
import { 
  LayoutDashboard, 
  ScanLine, 
  History, 
  User as UserIcon, 
  ShieldAlert, 
  LogOut, 
  Bell, 
  ChevronDown, 
  Globe, 
  Check,
  TrendingUp,
  Activity,
  Droplet
} from 'lucide-react';
import { predictionsAPI } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import ChatWidget from './ChatWidget';
import styles from './Layout.module.css';

const Layout = () => {
  const { user, logout, isAdmin } = useAuth();
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const [isLangOpen, setIsLangOpen] = useState(false);
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const dropdownRef = useRef(null);
  const notifRef = useRef(null);

  // Language state
  const [currentLang, setCurrentLang] = useState(() => 
    localStorage.getItem('mediascan_lang') || 'en'
  );

  const languages = [
    { code: 'en', name: 'English', flag: '🇬🇧' },
    { code: 'hi', name: 'हिंदी', flag: '🇮🇳' },
    { code: 'mr', name: 'मराठी', flag: '🇮🇳' },
    { code: 'gu', name: 'ગુજરાતી', flag: '🇮🇳' }
  ];

  const sidebarNav = [
    { name: t('sidebar.dashboard'), path: '/dashboard', icon: <LayoutDashboard /> },
    { name: t('sidebar.new_scan'), path: '/scan', icon: <ScanLine /> },
    { name: t('sidebar.history'), path: '/history', icon: <History /> },
    { name: t('sidebar.ml_analysis'), path: '/ml-analysis', icon: <TrendingUp /> },
    { name: t('sidebar.profile'), path: '/profile', icon: <UserIcon /> },
  ];

  const adminNav = { name: t('sidebar.admin'), path: '/admin', icon: <ShieldAlert /> };

  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        const res = await predictionsAPI.getHistory(1, 5);
        setNotifications(res.data.predictions || []);
      } catch (err) {
        console.error("Notification sync failed", err);
      }
    };
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 60000); // Polling every minute
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsLangOpen(false);
      }
      if (notifRef.current && !notifRef.current.contains(event.target)) {
        setIsNotifOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLangSelect = (code) => {
    setCurrentLang(code);
    i18n.changeLanguage(code);
    localStorage.setItem('mediascan_lang', code);
    setIsLangOpen(false);
  };

  const getActiveLang = () => languages.find(l => l.code === currentLang) || languages[0];

  const handleSignOut = () => {
    logout();
    navigate('/login');
  };

  const pageTitle = sidebarNav.find(n => n.path === location.pathname)?.name || 
                    (location.pathname === '/admin' ? 'Admin Intelligence' : 'MediScan AI');

  return (
    <div className={styles.shell} style={{ display: 'flex', minHeight: '100vh', background: '#f8fafc' }}>
      {/* Sidebar v3: Ultra-Wide Authority */}
      <aside className={styles.sidebar} style={{ 
        width: '420px', 
        height: '100vh', 
        position: 'fixed', 
        left: 0, 
        top: 0, 
        background: '#ffffff', 
        borderRight: '1px solid #e2e8f0',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 100,
        boxShadow: '10px 0 40px rgba(0,0,0,0.03)'
      }}>
        {/* Expanded Brand Header */}
        <div style={{ padding: '56px 40px', display: 'flex', alignItems: 'center', gap: '24px' }}>
          <div style={{ 
            width: '84px', height: '84px', background: 'linear-gradient(135deg, #1a56db, #2563eb)', 
            borderRadius: '24px', display: 'flex', alignItems: 'center', justifyContent: 'center', 
            color: '#fff', boxShadow: '0 12px 24px rgba(26,86,219,0.3)'
          }}>
            <Activity size={48} strokeWidth={3} />
          </div>
          <span style={{ fontSize: '42px', fontWeight: 900, color: '#111827', fontFamily: "'Outfit', sans-serif", letterSpacing: '-2px' }}>MediScan AI</span>
        </div>

        {/* Scaled Navigation Items */}
        <nav style={{ flex: 1, padding: '0 20px' }}>
          {sidebarNav.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link 
                key={item.path} 
                to={item.path}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '24px',
                  padding: '20px 28px',
                  marginBottom: '12px',
                  borderRadius: '20px',
                  textDecoration: 'none',
                  color: isActive ? '#1a56db' : '#64748b',
                  background: isActive ? '#eff6ff' : 'transparent',
                  fontFamily: "'DM Sans', sans-serif",
                  fontWeight: isActive ? 900 : 700,
                  fontSize: '28px',
                  transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
                  borderLeft: isActive ? '6px solid #1a56db' : '6px solid transparent',
                  boxShadow: isActive ? '0 4px 12px rgba(26,86,219,0.05)' : 'none'
                }}
              >
                <span style={{ display: 'flex', alignItems: 'center' }}>
                  {React.cloneElement(item.icon, { size: 42, strokeWidth: isActive ? 3 : 2.5 })}
                </span>
                {item.name}
              </Link>
            );
          })}

          {isAdmin && (
             <Link 
                to={adminNav.path}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '24px',
                  padding: '20px 28px',
                  marginTop: '32px',
                  borderRadius: '20px',
                  textDecoration: 'none',
                  color: location.pathname === '/admin' ? '#1a56db' : '#64748b',
                  background: location.pathname === '/admin' ? '#eff6ff' : 'transparent',
                  fontFamily: "'DM Sans', sans-serif",
                  fontWeight: location.pathname === '/admin' ? 900 : 700,
                  fontSize: '28px',
                  transition: 'all 0.3s',
                  borderLeft: location.pathname === '/admin' ? '6px solid #1a56db' : '6px solid transparent',
                  borderTop: '1px solid #f1f5f9', 
                  paddingTop: '40px'
                }}
              >
                <span style={{ display: 'flex', alignItems: 'center' }}>
                  {React.cloneElement(adminNav.icon, { size: 42, strokeWidth: location.pathname === '/admin' ? 3 : 2.5 })}
                </span>
                {adminNav.name}
              </Link>
          )}
        </nav>


        <div style={{ padding: '32px', borderTop: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{
            width: '68px', height: '68px', borderRadius: '50%', background: '#f8fafc',
            display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#1a56db', fontWeight: 900,
            fontSize: '24px', border: '1px solid #e2e8f0', boxShadow: '0 4px 10px rgba(0,0,0,0.02)'
          }}>
             {user?.name?.[0]}
          </div>
          <div style={{ flex: 1, overflow: 'hidden' }}>
             <div style={{ fontFamily: "'DM Sans', sans-serif", fontSize: '24px', fontWeight: 900, color: '#111827', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user?.name}</div>
             <div style={{ fontFamily: "'DM Sans', sans-serif", fontSize: '18px', color: '#64748b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user?.email}</div>
          </div>
        </div>
      </aside>

      {/* Fluid Main Content Area */}
      <div className={styles.main} style={{ 
        marginLeft: '420px', 
        flex: 1, 
        minHeight: '100vh',
        background: '#f8fafc',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Transparent Modern Header */}
        <header className={styles.header} style={{ 
          height: '112px', 
          background: 'rgba(255,255,255,0.85)', 
          backdropFilter: 'blur(16px)',
          borderBottom: '1px solid #e2e8f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 5vw',
          position: 'sticky',
          top: 0,
          zIndex: 90
        }}>
          <h2 style={{ fontSize: '34px', fontWeight: 900, color: '#111827', fontFamily: "'Outfit', sans-serif", letterSpacing: '-1.5px' }}>{pageTitle}</h2>

          <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
            {/* High-Fidelity Language Switcher */}
            <div style={{ position: 'relative' }} ref={dropdownRef}>
              <button
                onClick={() => setIsLangOpen(!isLangOpen)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '12px', padding: '14px 28px',
                  background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '999px',
                  cursor: 'pointer', transition: 'all 0.3s', boxShadow: '0 4px 6px rgba(0,0,0,0.02)'
                }}
              >
                <Globe size={26} color="#1a56db" />
                <span style={{ fontSize: '24px', fontWeight: 900, color: '#334155', fontFamily: "'DM Sans', sans-serif" }}>{getActiveLang().name}</span>
                <ChevronDown size={20} color="#94a3b8" />
              </button>

              {isLangOpen && (
                <div style={{
                  position: 'absolute', top: '115%', right: 0, minWidth: '240px',
                  background: '#fff', border: '1px solid #e2e8f0', borderRadius: '20px',
                  boxShadow: '0 20px 40px rgba(0,0,0,0.12)', padding: '12px', zIndex: 200,
                  animation: 'fadeIn 0.2s ease-out'
                }}>
                  {languages.map(lang => (
                    <div
                      key={lang.code}
                      onClick={() => handleLangSelect(lang.code)}
                      style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        padding: '14px 18px', borderRadius: '14px', cursor: 'pointer',
                        background: currentLang === lang.code ? '#eff6ff' : 'transparent',
                        color: currentLang === lang.code ? '#1a56db' : '#475569',
                        transition: '0.2s'
                      }}
                      onMouseOver={(e) => {
                        if (currentLang !== lang.code) e.currentTarget.style.background = '#f8fafc';
                      }}
                      onMouseOut={(e) => {
                        if (currentLang !== lang.code) e.currentTarget.style.background = 'transparent';
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span style={{ fontSize: '24px' }}>{lang.flag}</span>
                        <span style={{ fontSize: '22px', fontWeight: currentLang === lang.code ? 900 : 600 }}>{lang.name}</span>
                      </div>
                      {currentLang === lang.code && <Check size={24} />}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div style={{ position: 'relative' }} ref={notifRef}>
              <button 
                onClick={() => setIsNotifOpen(!isNotifOpen)}
                style={{
                  width: '52px', height: '52px', borderRadius: '16px', border: '1px solid #e2e8f0',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fff',
                  color: isNotifOpen ? '#1a56db' : '#64748b', cursor: 'pointer', transition: 'all 0.3s',
                  position: 'relative'
                }}
              >
                <Bell size={24} strokeWidth={isNotifOpen ? 3 : 2} />
                {notifications.length > 0 && (
                  <span style={{
                    position: 'absolute', top: '12px', right: '12px', width: '12px', height: '12px',
                    background: '#ef4444', borderRadius: '50%', border: '2px solid #fff'
                  }} />
                )}
              </button>

              {isNotifOpen && (
                <div style={{
                  position: 'absolute', top: '115%', right: 0, width: '420px',
                  background: '#fff', border: '1px solid #e2e8f0', borderRadius: '24px',
                  boxShadow: '0 20px 40px rgba(0,0,0,0.12)', padding: '24px', zIndex: 200,
                  animation: 'fadeIn 0.2s ease-out'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                    <h3 style={{ fontSize: '24px', fontWeight: 900, color: '#111827', fontFamily: "'Outfit', sans-serif" }}>Recent Activity</h3>
                    <Link to="/history" onClick={() => setIsNotifOpen(false)} style={{ fontSize: '18px', fontWeight: 800, color: '#1a56db', textDecoration: 'none' }}>View All</Link>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {notifications.length > 0 ? notifications.map((notif) => (
                      <Link 
                        key={notif.id} 
                        to={`/results/${notif.id}`}
                        onClick={() => setIsNotifOpen(false)}
                        style={{
                          display: 'flex', alignItems: 'center', gap: '16px', padding: '16px',
                          borderRadius: '16px', textDecoration: 'none', background: '#f8fafc',
                          transition: '0.2s', border: '1px solid transparent'
                        }}
                        onMouseOver={(e) => { e.currentTarget.style.borderColor = '#1a56db'; e.currentTarget.style.background = '#eff6ff'; }}
                        onMouseOut={(e) => { e.currentTarget.style.borderColor = 'transparent'; e.currentTarget.style.background = '#f8fafc'; }}
                      >
                        <div style={{
                          width: '48px', height: '48px', borderRadius: '12px', background: '#fff',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#1a56db',
                          boxShadow: '0 4px 6px rgba(0,0,0,0.02)'
                        }}>
                          {notif.model_type === 'eye' && <Activity size={20} />}
                          {notif.model_type === 'palm' && <Droplet size={20} />}
                          {notif.model_type === 'retina' && <Activity size={20} />}
                          {notif.model_type === 'skin' && <Activity size={20} />}
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: '18px', fontWeight: 800, color: '#1e293b' }}>
                            {notif.primary_diagnosis} Update
                          </div>
                          <div style={{ fontSize: '16px', color: '#64748b', fontWeight: 500 }}>
                            Result: <span style={{ fontWeight: 800, color: notif.primary_risk_level === 'high' ? '#dc2626' : '#059669' }}>{notif.primary_status}</span>
                          </div>
                        </div>
                      </Link>
                    )) : (
                      <div style={{ padding: '40px 0', textAlign: 'center', color: '#94a3b8' }}>
                        No recent notifications.
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '20px', paddingLeft: '32px', borderLeft: '1px solid #e2e8f0' }}>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '21px', fontWeight: 900, color: '#111827', fontFamily: "'DM Sans', sans-serif" }}>{user?.name}</div>
                <div style={{ 
                    fontSize: '18px', color: '#64748b', textTransform: 'uppercase', 
                    letterSpacing: '1px', fontWeight: 800, fontFamily: "'DM Sans', sans-serif"
                }}>
                    {user?.role === 'admin' ? t('header.administrator') : t('header.medical_member')}
                </div>
              </div>
              <button 
                onClick={handleSignOut}
                style={{
                  width: '40px', height: '40px', borderRadius: '10px', background: '#fef2f2',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ef4444',
                  border: 'none', cursor: 'pointer', transition: 'all 0.2s'
                }}
                onMouseOver={(e) => e.currentTarget.style.background = '#fee2e2'}
                onMouseOut={(e) => e.currentTarget.style.background = '#fef2f2'}
              >
                <LogOut size={20} />
              </button>
            </div>
          </div>
        </header>

        {/* Universal Outlet Area */}
        <main style={{ flex: 1, padding: '0' }}>
          <Outlet />
        </main>
      </div>

      {/* Chatbot widget — only when authenticated */}
      {user && <ChatWidget />}

      <style>{`
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};

export default Layout;
