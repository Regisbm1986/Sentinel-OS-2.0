import {FormEvent, useMemo, useState} from 'react';
import type {CSSProperties} from 'react';
import {useLocation, useNavigate} from 'react-router-dom';
import {apiFetch} from '../lib/apiClient';

const pageStyle: CSSProperties = {
  minHeight: '100vh',
  padding: '48px 20px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background:
    'radial-gradient(circle at 16% 12%, rgba(58, 247, 198, 0.20), transparent 420px), ' +
    'radial-gradient(circle at 82% 8%, rgba(74, 163, 255, 0.22), transparent 480px), ' +
    '#030712',
  color: '#f4f7fb',
  fontFamily: '"Inter", "Segoe UI", system-ui, sans-serif',
};

const shellStyle: CSSProperties = {
  width: 'min(100%, 1120px)',
  display: 'grid',
  gap: '36px',
  gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
  alignItems: 'stretch',
};

const cardStyle: CSSProperties = {
  position: 'relative',
  padding: '48px',
  borderRadius: '28px',
  background: 'rgba(9, 15, 30, 0.9)',
  border: '1px solid rgba(58, 247, 198, 0.28)',
  boxShadow: '0 40px 120px -50px rgba(58, 247, 198, 0.55)',
  backdropFilter: 'blur(18px)',
  display: 'flex',
  flexDirection: 'column',
  gap: '28px',
};

const asideStyle: CSSProperties = {
  borderRadius: '28px',
  padding: '44px',
  background: 'linear-gradient(140deg, rgba(9, 25, 42, 0.92), rgba(9, 17, 32, 0.82))',
  border: '1px solid rgba(74, 163, 255, 0.32)',
  boxShadow: '0 40px 120px -48px rgba(74, 163, 255, 0.55)',
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'center',
  gap: '24px',
};

const socialButtonStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '12px',
  padding: '14px 18px',
  borderRadius: '14px',
  border: '1px solid rgba(148, 163, 184, 0.28)',
  background: 'rgba(6, 12, 22, 0.88)',
  color: '#f8fafc',
  fontWeight: 600,
  fontSize: '0.98rem',
  cursor: 'pointer',
  transition: 'transform 0.18s ease, border-color 0.18s ease, background 0.18s ease',
};

const inputStyle: CSSProperties = {
  width: '100%',
  padding: '14px 16px',
  borderRadius: '14px',
  border: '1px solid rgba(58, 247, 198, 0.32)',
  background: 'rgba(7, 15, 26, 0.86)',
  color: '#f8fafc',
  fontSize: '1rem',
  transition: 'border-color 0.18s ease, box-shadow 0.18s ease',
};

const primaryButtonStyle: CSSProperties = {
  width: '100%',
  display: 'inline-flex',
  justifyContent: 'center',
  alignItems: 'center',
  gap: '10px',
  padding: '14px 18px',
  borderRadius: '14px',
  border: 'none',
  background: 'linear-gradient(120deg, #38d6ae, #4aa3ff)',
  color: '#030712',
  fontWeight: 700,
  fontSize: '1rem',
  cursor: 'pointer',
  transition: 'transform 0.18s ease, box-shadow 0.18s ease',
};

const metricStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  padding: '12px 16px',
  borderRadius: '16px',
  border: '1px solid rgba(58, 247, 198, 0.28)',
  background: 'rgba(6, 17, 28, 0.82)',
  color: 'rgba(165, 243, 252, 0.9)',
  fontWeight: 600,
  fontSize: '0.95rem',
};

const dividerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '12px',
  color: 'rgba(200, 212, 228, 0.64)',
  fontSize: '0.9rem',
};

const dividerLine: CSSProperties = {
  flex: 1,
  height: '1px',
  background: 'linear-gradient(90deg, transparent, rgba(148, 163, 184, 0.38))',
};

const brandBadgeStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '12px',
  textTransform: 'uppercase',
  letterSpacing: '0.24em',
  fontSize: '0.72rem',
  color: 'rgba(148, 237, 255, 0.82)',
};

const socialIconStyle: CSSProperties = {
  height: '20px',
  width: '20px',
};

const errorStyle: CSSProperties = {
  marginBottom: '18px',
  padding: '14px 16px',
  borderRadius: '12px',
  border: '1px solid rgba(252, 165, 165, 0.45)',
  background: 'rgba(82, 12, 26, 0.62)',
  color: '#fecaca',
  fontSize: '0.92rem',
};

export default function LoginPage(): JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [socialLoading, setSocialLoading] = useState<{google: boolean; linkedin: boolean}>({google: false, linkedin: false});

  const nextPath = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return params.get('next') || '/dashboard';
  }, [location.search]);

  const handleEmailLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSubmitting) {
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const response = await apiFetch('/api/auth/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        credentials: 'include',
        body: JSON.stringify({email, password, next_url: nextPath}),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        const message = payload?.detail ?? 'Não foi possível autenticar. Verifique suas credenciais.';
        setError(message);
        setIsSubmitting(false);
        return;
      }

      const payload = await response.json().catch(() => ({}));
      const redirectTo = typeof payload?.redirect_to === 'string' ? payload.redirect_to : '/dashboard';
      navigate(redirectTo, {replace: true});
    } catch (err) {
      setError('Falha ao se comunicar com o servidor. Tente novamente em instantes.');
      setIsSubmitting(false);
    }
  };

  const startSocialLogin = async (provider: 'google' | 'linkedin') => {
    if (socialLoading[provider]) {
      return;
    }

    setError(null);
    setSocialLoading((prev) => ({...prev, [provider]: true}));

    const query = nextPath ? `?next=${encodeURIComponent(nextPath)}` : '';

    try {
      const response = await apiFetch(`/api/auth/${provider}/login${query}`, {credentials: 'include'});
      if (!response.ok) {
        throw new Error('Falha ao iniciar autenticação social.');
      }
      const payload = await response.json();
      if (typeof payload?.authorization_url === 'string') {
        window.location.href = payload.authorization_url;
        return;
      }
      if (typeof payload?.redirect_to === 'string') {
        window.location.href = payload.redirect_to;
        return;
      }
      throw new Error('Resposta inesperada do provedor de login.');
    } catch (err) {
      const fallbackMessage = err instanceof Error ? err.message : 'Não foi possível iniciar o login social.';
      setError(fallbackMessage);
    } finally {
      setSocialLoading((prev) => ({...prev, [provider]: false}));
    }
  };

  const renderGoogleIcon = () => (
    <svg viewBox="0 0 48 48" style={socialIconStyle} aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6 1.54 7.38 2.83l5.43-5.42C33.89 3.36 29.36 1 24 1 14.82 1 6.92 6.62 3.64 14.53l6.84 5.31C12.27 14.12 17.64 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.5 24.5c0-1.64-.15-3.21-.44-4.74H24v9h12.7c-.55 2.96-2.26 5.48-4.82 7.16l6.84 5.31C43.71 37.79 46.5 31.7 46.5 24.5z" />
      <path fill="#FBBC05" d="M10.48 28.34c-.48-1.41-.75-2.92-.75-4.34s.27-2.93.75-4.34l-6.84-5.31C1.67 17.13 0.5 20.37 0.5 24c0 3.63 1.17 6.87 3.15 9.65l6.83-5.31z" />
      <path fill="#34A853" d="M24 47c6.48 0 11.9-2.14 15.87-5.84l-6.84-5.31C30.41 37.66 27.41 39 24 39c-6.36 0-11.73-4.62-13.53-10.34l-6.84 5.31C6.92 41.38 14.82 47 24 47z" />
    </svg>
  );

  const renderLinkedInIcon = () => (
    <svg viewBox="0 0 34 34" style={socialIconStyle} aria-hidden="true">
      <path
        fill="#0A66C2"
        d="M34 34h-7.06V23.54c0-2.5-.9-4.2-3.17-4.2-1.73 0-2.75 1.16-3.21 2.28-.17.41-.21.98-.21 1.55V34H13.3s.09-18.73 0-20.68h7.06v2.93c.94-1.45 2.62-3.53 6.38-3.53 4.66 0 8.26 3.05 8.26 9.62V34z"
      />
      <path
        fill="#0A66C2"
        d="M4.02 10.61c-2.41 0-3.98-1.59-3.98-3.57 0-2.02 1.6-3.56 4.05-3.56 2.45 0 3.98 1.54 4.03 3.56 0 1.99-1.58 3.57-4.1 3.57zM.44 34h7.06V13.32H.44V34z"
      />
    </svg>
  );

  return (
    <div style={pageStyle}>
      <div style={shellStyle}>
        <section style={cardStyle}>
          <div style={brandBadgeStyle}>
            <img src="/static/images/logo-career-horizontal.png" alt="Sentinel Career" style={{height: '60px', width: 'auto'}} />
            <span>SENTINEL CAREER · Carreira potencializada por IA</span>
          </div>

          <div>
            <h1 style={{margin: '0 0 12px', fontSize: 'clamp(2rem, 4vw, 2.8rem)', fontWeight: 700}}>Acesse sua jornada inteligente</h1>
            <p style={{margin: 0, color: 'rgba(173, 195, 219, 0.82)', lineHeight: 1.6}}>
              Conecte-se com autenticação corporativa, confiança Sentinel e monitoramento contínuo de segurança.
            </p>
          </div>

          <div style={{display: 'flex', flexDirection: 'column', gap: '12px'}}>
            <button
              type="button"
              style={{...socialButtonStyle, borderColor: 'rgba(234, 67, 53, 0.18)'}}
              onClick={() => startSocialLogin('google')}
              disabled={socialLoading.google}
            >
              {renderGoogleIcon()}
              <span>{socialLoading.google ? 'Conectando Google...' : 'Entrar com Google'}</span>
            </button>
            <button
              type="button"
              style={{...socialButtonStyle, borderColor: 'rgba(10, 102, 194, 0.28)'}}
              onClick={() => startSocialLogin('linkedin')}
              disabled={socialLoading.linkedin}
            >
              {renderLinkedInIcon()}
              <span>{socialLoading.linkedin ? 'Conectando LinkedIn...' : 'Entrar com LinkedIn'}</span>
            </button>
          </div>

          <div style={dividerStyle}>
            <span style={dividerLine} />
            <span>ou utilize credenciais corporativas</span>
            <span style={dividerLine} />
          </div>

          {error ? <div style={errorStyle}>{error}</div> : null}

          <form style={{display: 'flex', flexDirection: 'column', gap: '18px'}} onSubmit={handleEmailLogin} noValidate>
            <input type="hidden" name="next" value={nextPath} />
            <label style={{fontSize: '0.9rem', fontWeight: 500, color: 'rgba(222, 231, 244, 0.88)'}}>
              E-mail corporativo
              <input
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                style={inputStyle}
                placeholder="voce@sentinel.ai"
              />
            </label>

            <label style={{fontSize: '0.9rem', fontWeight: 500, color: 'rgba(222, 231, 244, 0.88)'}}>
              Senha
              <input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                style={inputStyle}
                placeholder="••••••••"
              />
            </label>

            <button type="submit" style={primaryButtonStyle} disabled={isSubmitting}>
              {isSubmitting ? 'Validando credenciais...' : 'Entrar com e-mail'}
            </button>
          </form>

          <p style={{margin: 0, fontSize: '0.88rem', color: 'rgba(148, 163, 184, 0.75)', textAlign: 'center'}}>
            Ao continuar, você concorda com nossas políticas de segurança e uso responsável de IA.
          </p>

          <p style={{margin: 0, fontSize: '0.9rem', color: 'rgba(233, 246, 255, 0.82)', textAlign: 'center'}}>
            Não tem uma conta?{' '}
            <a href="/register" style={{color: '#61f7d2', fontWeight: 600, textDecoration: 'none'}}>
              Faça seu cadastro
            </a>
          </p>
        </section>

        <aside style={asideStyle}>
          <div>
            <h2 style={{margin: '0 0 12px', fontSize: '1.8rem', fontWeight: 600, color: '#e2f1ff'}}>Trust Center Sentinel</h2>
            <p style={{margin: 0, color: 'rgba(185, 202, 224, 0.85)', lineHeight: 1.6}}>
              Single Sign-On federado, monitoramento 24/7 e criptografia ponta a ponta protegendo cada sessão da sua equipe.
            </p>
          </div>

          <div style={{display: 'flex', flexDirection: 'column', gap: '14px'}}>
            <div style={metricStyle}>🔐 Sessões protegidas por AI Threat Guard</div>
            <div style={metricStyle}>⚡ Autenticação média em 1,8s com SSO</div>
            <div style={metricStyle}>📊 99,99% de uptime nos últimos 12 meses</div>
          </div>

          <p style={{margin: 0, color: 'rgba(148, 163, 184, 0.72)', fontSize: '0.85rem'}}>
            Precisa de ajuda? <a href="mailto:support@sentinel.ai" style={{color: '#4aa3ff', fontWeight: 600, textDecoration: 'none'}}>contate o suporte especializado</a>.
          </p>
        </aside>
      </div>
    </div>
  );
}
