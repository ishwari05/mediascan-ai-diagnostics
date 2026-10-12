import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Mail, 
  Lock, 
  Eye, 
  EyeOff, 
  Shield, 
  Search, 
  LockKeyhole, 
  FileText 
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import s from './LoginPage.module.css';

const LoginPage = () => {
    const { t } = useTranslation();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    
    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const success = await login(email, password);
            if (success) {
                toast.success(t('auth.welcome_back_toast'));
                navigate('/dashboard');
            }
        } catch (err) {
            toast.error(err.response?.data?.error || t('auth.login_failed'));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={s.page} style={{ 
            display: 'flex', 
            minHeight: '100vh', 
            background: '#ffffff', 
            fontFamily: "'DM+Sans', sans-serif",
            overflow: 'hidden'
        }}>
            {/* LEFT PANEL: 50% width, gradient, hidden on mobile */}
            <div className={`${s.leftPanel} desktop-only-panel`} style={{ 
                flex: 1, 
                background: 'linear-gradient(160deg, #1e3a5f 0%, #1a56db 60%, #2563eb 100%)',
                padding: '48px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                color: '#ffffff',
                // Responsive: show only on desktop
                '@media (maxWidth: 768px)': { display: 'none' }
            }}>
                <style>{`
                    @media (max-width: 768px) {
                        .desktop-only-panel { display: none !important; }
                    }
                `}</style>
                
                {/* TOP — Logo row */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                    <Shield size={52} color="white" fill="rgba(255,255,255,0.2)" />
                    <div>
                        <div style={{ 
                            fontSize: '34px', 
                            fontWeight: 900, 
                            fontFamily: "'Outfit', sans-serif",
                            letterSpacing: '-1px',
                            lineHeight: 1
                        }}>MediScan AI</div>
                        <div style={{ 
                            fontSize: '14px', 
                            fontWeight: 800, 
                            color: 'rgba(255,255,255,0.7)', 
                            textTransform: 'uppercase', 
                            letterSpacing: '2px',
                            fontFamily: "'DM Sans', sans-serif",
                            marginTop: '2px'
                        }}>HEALTH INTELLIGENCE PLATFORM</div>
                    </div>
                </div>

                {/* CENTER — Hero text */}
                <div style={{ margin: 'auto 0' }}>
                    <h1 style={{ 
                        fontFamily: "'Outfit', sans-serif",
                        fontSize: '84px', 
                        fontWeight: 900, 
                        lineHeight: 0.95,
                        margin: 0,
                        letterSpacing: '-4px'
                    }}>
                        {t('auth.hero_title_1')}<br />
                        {t('auth.hero_title_2')}<br />
                        {t('auth.hero_title_3')}
                    </h1>
                    <p style={{ 
                        fontSize: '24px', 
                        opacity: 0.9, 
                        marginTop: '32px', 
                        lineHeight: 1.6,
                        maxWidth: '640px',
                        fontFamily: "'DM Sans', sans-serif",
                        fontWeight: 500
                    }}>
                        {t('auth.hero_subtitle')}
                    </p>

                    {/* Three feature mini-cards */}
                    <div style={{ display: 'flex', gap: '14px', marginTop: '48px' }}>
                        {[
                            { icon: <Search size={28} />, title: t('auth.feat_1_title'), desc: t('auth.feat_1_desc') },
                            { icon: <Shield size={28} />, title: t('auth.feat_2_title'), desc: t('auth.feat_2_desc') },
                            { icon: <FileText size={28} />, title: t('auth.feat_3_title'), desc: t('auth.feat_3_desc') }
                        ].map((card, i) => (
                            <div key={i} style={{ 
                                background: 'rgba(255,255,255,0.1)', 
                                borderRadius: '20px', 
                                padding: '24px', 
                                flex: 1,
                                border: '1px solid rgba(255,255,255,0.1)'
                            }}>
                                <div style={{ color: 'white', marginBottom: '14px' }}>{card.icon}</div>
                                <div style={{ fontSize: '22px', fontWeight: 800, color: 'white', fontFamily: "'Outfit', sans-serif" }}>{card.title}</div>
                                <div style={{ fontSize: '17px', color: 'rgba(255,255,255,0.7)', fontFamily: "'DM Sans', sans-serif", marginTop: '6px', fontWeight: 500 }}>{card.desc}</div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* BOTTOM — Testimonial */}
                <div style={{ marginTop: 'auto', paddingTop: '64px' }}>
                    <div style={{ color: '#fbbf24', fontSize: '28px', marginBottom: '16px' }}>★★★★★</div>
                    <p style={{ 
                        color: 'rgba(255,255,255,0.95)', 
                        fontSize: '22px', 
                        fontStyle: 'italic', 
                        lineHeight: 1.6,
                        marginBottom: '32px',
                        fontFamily: "'DM Sans', sans-serif",
                        fontWeight: 600
                    }}>
                        "{t('auth.testimonial_text')}"
                    </p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <div style={{ 
                            width: '52px', 
                            height: '52px', 
                            borderRadius: '52px', 
                            background: 'linear-gradient(135deg, #1a56db, #06b6d4)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'white',
                            fontSize: '18px',
                            fontWeight: 800
                        }}>RS</div>
                        <div>
                            <div style={{ fontSize: '16px', fontWeight: 700, color: 'white' }}>{t('auth.testimonial_author')}</div>
                            <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.6)', fontWeight: 600 }}>{t('auth.verified_user')}</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* RIGHT PANEL: 50% width, white background, form */}
            <div className={s.rightPanel} style={{ 
                flex: 1, 
                background: '#ffffff', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center', 
                padding: '64px 48px' 
            }}>
                <div className={s.formCard} style={{ maxWidth: '720px', width: '100%', margin: 'auto' }}>
                    
                    {/* Logo (Mobile Only) */}
                    <div style={{ 
                        display: 'none', 
                        textAlign: 'center', 
                        marginBottom: '32px',
                        '@media (maxWidth: 768px)': { display: 'block' }
                    }} className="mobile-logo">
                        <style>{`
                            @media (max-width: 768px) {
                                .mobile-logo { display: block !important; }
                            }
                        `}</style>
                        <div style={{ 
                            width: '36px', 
                            height: '36px', 
                            borderRadius: '50%', 
                            background: 'linear-gradient(135deg, #1a56db, #2563eb)',
                            margin: '0 auto 12px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'white'
                        }}><Shield size={20} /></div>
                        <div style={{ fontSize: '18px', fontWeight: 700, color: '#111827' }}>MediScan AI</div>
                    </div>

                    <h2 className={s.formTitle} style={{ 
                        fontFamily: "'Outfit', sans-serif", 
                        fontWeight: 900, 
                        fontSize: '56px', 
                        color: '#111827', 
                        marginBottom: '16px',
                        letterSpacing: '-2px'
                    }}>{t('auth.login_title')}</h2>
                    <p className={s.formSubtitle} style={{ 
                        fontSize: '22px', 
                        color: '#64748b', 
                        fontWeight: 500, 
                        marginBottom: '48px',
                        fontFamily: "'DM Sans', sans-serif"
                    }}>{t('auth.login_subtitle')}</p>

                    <form onSubmit={handleSubmit}>
                        {/* Email field */}
                        <div className={s.inputGroup} style={{ marginBottom: '24px' }}>
                            <label className={s.inputLabel} style={{ 
                                display: 'block', 
                                fontSize: '21px', 
                                fontWeight: 800, 
                                color: '#111827', 
                                marginBottom: '12px',
                                fontFamily: "'DM Sans', sans-serif"
                            }}>{t('auth.email')}</label>
                            <div className={s.inputWrapper} style={{ position: 'relative' }}>
                                <Mail 
                                    className={s.inputIcon}
                                    size={24} 
                                    style={{ 
                                        position: 'absolute', 
                                        left: '20px', 
                                        top: '22px', 
                                        color: '#94a3b8' 
                                    }} 
                                />
                                <input 
                                    className={s.input}
                                    type="email" 
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="you@example.com"
                                    required
                                    style={{
                                        width: '100%',
                                        height: '68px',
                                        padding: '0 20px 0 60px',
                                        border: '1px solid #dde3f4',
                                        borderRadius: '16px',
                                        fontSize: '21px',
                                        color: '#111827',
                                        background: '#ffffff',
                                        outline: 'none',
                                        transition: 'all 0.2s',
                                        fontFamily: "'DM Sans', sans-serif"
                                    }}
                                    onFocus={(e) => {
                                        e.target.style.borderColor = '#1a56db';
                                        e.target.style.boxShadow = '0 0 0 3px rgba(26,86,219,0.12)';
                                    }}
                                    onBlur={(e) => {
                                        e.target.style.borderColor = '#dde3f4';
                                        e.target.style.boxShadow = 'none';
                                    }}
                                />
                            </div>
                        </div>

                        {/* Password field */}
                        <div className={s.inputGroup} style={{ marginBottom: '12px' }}>
                            <label className={s.inputLabel} style={{ 
                                display: 'block', 
                                fontSize: '21px', 
                                fontWeight: 800, 
                                color: '#111827', 
                                marginBottom: '12px',
                                fontFamily: "'DM Sans', sans-serif"
                            }}>{t('auth.password')}</label>
                            <div className={s.inputWrapper} style={{ position: 'relative' }}>
                                <LockKeyhole 
                                    className={s.inputIcon}
                                    size={24} 
                                    style={{ 
                                        position: 'absolute', 
                                        left: '20px', 
                                        top: '22px', 
                                        color: '#94a3b8' 
                                    }} 
                                />
                                <input 
                                    className={s.input}
                                    type={showPassword ? "text" : "password"}
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder={t('auth.password_placeholder')}
                                    required
                                    style={{
                                        width: '100%',
                                        height: '68px',
                                        padding: '0 64px 0 60px',
                                        border: '1px solid #dde3f4',
                                        borderRadius: '16px',
                                        fontSize: '21px',
                                        color: '#111827',
                                        background: '#ffffff',
                                        outline: 'none',
                                        transition: 'all 0.2s',
                                        fontFamily: "'DM Sans', sans-serif"
                                    }}
                                    onFocus={(e) => {
                                        e.target.style.borderColor = '#1a56db';
                                        e.target.style.boxShadow = '0 0 0 3px rgba(26,86,219,0.12)';
                                    }}
                                    onBlur={(e) => {
                                        e.target.style.borderColor = '#dde3f4';
                                        e.target.style.boxShadow = 'none';
                                    }}
                                />
                                <div 
                                    className={s.pwToggle}
                                    onClick={() => setShowPassword(!showPassword)}
                                    style={{ 
                                        position: 'absolute', 
                                        right: '14px', 
                                        top: '14px', 
                                        cursor: 'pointer', 
                                        color: '#9ca3af' 
                                    }}
                                >
                                    {showPassword ? <EyeOff size={22} /> : <Eye size={22} />}
                                </div>
                            </div>
                        </div>

                        {/* Forgot Password Link */}
                        <div style={{ textAlign: 'right', marginBottom: '32px' }}>
                             <a href="#" style={{ 
                                 fontSize: '18px', 
                                 fontWeight: 700, 
                                 color: '#1a56db', 
                                 textDecoration: 'none',
                                 fontFamily: "'DM Sans', sans-serif"
                             }}>{t('auth.forgot_password')}</a>
                        </div>

                        {/* Submit Button */}
                        <button 
                            className={s.submitBtn}
                            type="submit" 
                            disabled={loading}
                            style={{
                                width: '100%',
                                height: '76px',
                                borderRadius: '20px',
                                border: 'none',
                                background: 'linear-gradient(135deg, #1a56db, #2563eb)',
                                color: 'white',
                                fontWeight: 900,
                                fontSize: '24px',
                                fontFamily: "'Outfit', sans-serif",
                                cursor: 'pointer',
                                boxShadow: '0 4px 16px rgba(26,86,219,0.3)',
                                transition: 'all 0.2s',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '8px'
                            }}
                            onMouseOver={(e) => {
                                e.currentTarget.style.transform = 'scale(1.01)';
                                e.currentTarget.style.boxShadow = '0 6px 24px rgba(26,86,219,0.4)';
                            }}
                            onMouseOut={(e) => {
                                e.currentTarget.style.transform = 'scale(1)';
                                e.currentTarget.style.boxShadow = '0 4px 16px rgba(26,86,219,0.3)';
                            }}
                        >
                            {loading ? (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <div style={{ 
                                        width: '18px', height: '18px', 
                                        border: '2px solid rgba(255,255,255,0.3)', 
                                        borderTopColor: '#fff', 
                                        borderRadius: '50%',
                                        animation: 'spin 0.8s linear infinite'
                                    }}></div>
                                    {t('auth.signing_in')}
                                </div>
                            ) : (
                                <>{t('auth.login_btn')} <ArrowRightIcon /></>
                            )}
                        </button>
                    </form>

                    {/* Sign up link row */}
                     <div className={s.switchLink} style={{ textAlign: 'center', marginTop: '32px' }}>
                        <span style={{ color: '#64748b', fontSize: '20px', fontFamily: "'DM Sans', sans-serif" }}>{t('auth.no_account')} </span>
                        <span 
                            onClick={() => navigate('/signup')}
                            style={{ 
                                color: '#1a56db', 
                                fontSize: '20px', 
                                fontWeight: 800, 
                                cursor: 'pointer',
                                fontFamily: "'DM Sans', sans-serif"
                            }}
                        >{t('auth.register')}</span>
                    </div>

                    {/* Footer text */}
                    <div style={{ textAlign: 'center', marginTop: '48px' }}>
                        <div style={{ 
                            fontSize: '11px', 
                            color: '#9ca3af', 
                            display: 'flex', 
                            alignItems: 'center', 
                            justifyContent: 'center', 
                            gap: '4px' 
                        }}>
                            <span>{t('auth.encrypted')}</span>
                            <span>·</span>
                            <span>{t('auth.privacy_safe')}</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <style>{`
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
};

// Shorthand icon for the button
const ArrowRightIcon = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <line x1="5" y1="12" x2="19" y2="12"></line>
        <polyline points="12 5 19 12 12 19"></polyline>
    </svg>
);

export default LoginPage;
