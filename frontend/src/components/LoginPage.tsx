import {FormEvent, useMemo, useState} from 'react';
import type {CSSProperties} from 'react';
import {useLocation, useNavigate} from 'react-router-dom';

const formShell: CSSProperties = {
  maxWidth: '420px',
  width: 'min(90%, 420px)',
  margin: '60px auto',
  padding: '36px',
  borderRadius: '20px',
  background: 'rgba(14, 21, 32, 0.86)',
  boxShadow: '0 24px 80px -32px rgba(58, 247, 198, 0.45)',
  border: '1px solid rgba(58, 247, 198, 0.35)',
  color: '#f2f7fb',
  fontFamily: '"Inter", "Segoe UI", system-ui, sans-serif',
};

const inputStyle: CSSProperties = {
  width: '100%',
  height: '48px',
  borderRadius: '12px',
  border: '1px solid rgba(255, 255, 255, 0.12)',
  background: 'rgba(28, 38, 52, 0.9)',
  color: '#f2f7fb',
  padding: '0 16px',
  fontSize: '0.98rem',
};

const buttonStyle: CSSProperties = {
  width: '100%',
  height: '52px',
  borderRadius: '999px',
  border: 'none',
  background: 'linear-gradient(135deg, #3af7c6, #2cd2aa)',
  color: '#04110d',
  fontWeight: 600,
  fontSize: '1rem',
  cursor: 'pointer',
  boxShadow: '0 20px 50px -18px rgba(58, 247, 198, 0.55)',
};

export default function LoginPage(): JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const nextPath = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return params.get('next') || '/dashboard';
  }, [location.search]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSubmitting) return;

    setError(null);
    setIsSubmitting(true);

    try {
      const response = await fetch('/api/auth/login', {
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

  return (
    <div style={{minHeight: '100vh', background: '#04070d', padding: '40px 12px'}}>
      <form onSubmit={handleSubmit} style={formShell}>
        <h1 style={{margin: '0 0 18px', fontSize: '1.9rem', fontWeight: 700}}>Entrar na Sentinel Career</h1>
        <p style={{margin: '0 0 24px', color: '#9aa8bb', fontSize: '0.98rem'}}>
          Acesse com suas credenciais corporativas para continuar a jornada assistida por IA.
        </p>

        <label style={{display: 'block', marginBottom: '18px'}}>
          <span style={{display: 'block', marginBottom: '8px', fontSize: '0.86rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#9aa8bb'}}>
            E-mail corporativo
          </span>
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

        <label style={{display: 'block', marginBottom: '24px'}}>
          <span style={{display: 'block', marginBottom: '8px', fontSize: '0.86rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#9aa8bb'}}>
            Senha
          </span>
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

        {error ? (
          <div style={{marginBottom: '18px', padding: '14px 16px', borderRadius: '12px', background: 'rgba(255, 77, 109, 0.12)', color: '#ff9aa6', fontSize: '0.92rem'}}>
            {error}
          </div>
        ) : null}

        <button type="submit" style={buttonStyle} disabled={isSubmitting}>
          {isSubmitting ? 'Entrando...' : 'Acessar Dashboard'}
        </button>

        <p style={{marginTop: '18px', color: '#9aa8bb', fontSize: '0.85rem'}}>
          Ao prosseguir, você concorda com nossas políticas de segurança e uso responsável de IA.
        </p>
      </form>
    </div>
  );
}
