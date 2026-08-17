import {FormEvent, useMemo, useState} from 'react';
import type {CSSProperties} from 'react';
import {useLocation, useNavigate} from 'react-router-dom';
import {apiFetch} from '../lib/apiClient';
import logoCareerHorizontal from '../assets/images/logo-career-horizontal.png';

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

const errorStyle: CSSProperties = {
  marginBottom: '18px',
  padding: '14px 16px',
  borderRadius: '12px',
  border: '1px solid rgba(252, 165, 165, 0.45)',
  background: 'rgba(82, 12, 26, 0.62)',
  color: '#fecaca',
  fontSize: '0.92rem',
};

export default function RegisterPage(): JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const nextPath = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return params.get('next') || '/dashboard';
  }, [location.search]);

  const handleRegister = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSubmitting) {
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const payload = {
        name,
        email,
        password,
        plan: 'FREE',
        next_url: nextPath,
      };

      const response = await apiFetch('/api/auth/register', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        credentials: 'include',
        body: JSON.stringify(payload),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const detail = typeof data?.detail === 'string' ? data.detail : 'Não foi possível concluir o cadastro.';
        setError(detail);
        setIsSubmitting(false);
        return;
      }

      const redirectTo = typeof data?.redirect_to === 'string' ? data.redirect_to : nextPath || '/dashboard';
      navigate(redirectTo, {replace: true});
    } catch (err) {
      setError('Falha ao se comunicar com o servidor. Tente novamente.');
      setIsSubmitting(false);
    }
  };

  return (
    <div style={pageStyle}>
      <div style={shellStyle}>
        <section style={cardStyle}>
          <div style={{display: 'flex', flexDirection: 'column', gap: '18px'}}>
            <img src={logoCareerHorizontal} alt="Sentinel Career" style={{height: '60px', width: 'auto'}} />
            <div>
              <h1 style={{margin: '0 0 12px', fontSize: 'clamp(2rem, 4vw, 2.8rem)', fontWeight: 700}}>Crie sua conta Sentinel Career</h1>
              <p style={{margin: 0, color: 'rgba(173, 195, 219, 0.82)', lineHeight: 1.6}}>
                Ative o plano Free e acompanhe em tempo real todos os insights de carreira fornecidos pelos agentes Sentinel OS.
              </p>
            </div>
          </div>

          {error ? <div style={errorStyle}>{error}</div> : null}

          <form style={{display: 'flex', flexDirection: 'column', gap: '18px'}} onSubmit={handleRegister} noValidate>
            <label style={{fontSize: '0.9rem', fontWeight: 500, color: 'rgba(222, 231, 244, 0.88)'}}>
              Nome completo
              <input
                type="text"
                autoComplete="name"
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
                style={inputStyle}
                placeholder="Seu nome completo"
              />
            </label>

            <label style={{fontSize: '0.9rem', fontWeight: 500, color: 'rgba(222, 231, 244, 0.88)'}}>
              E-mail corporativo
              <input
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                style={inputStyle}
                placeholder="contato@sentinel-os.ia.br"
              />
            </label>

            <label style={{fontSize: '0.9rem', fontWeight: 500, color: 'rgba(222, 231, 244, 0.88)'}}>
              Senha
              <input
                type="password"
                autoComplete="new-password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                style={inputStyle}
                placeholder="Defina uma senha segura"
              />
            </label>

            <button type="submit" style={primaryButtonStyle} disabled={isSubmitting}>
              {isSubmitting ? 'Criando conta...' : 'Finalizar cadastro'}
            </button>
          </form>

          <p style={{margin: 0, fontSize: '0.88rem', color: 'rgba(148, 163, 184, 0.75)', textAlign: 'center'}}>
            Ao continuar, você concorda com nossas políticas de segurança e uso responsável de IA.
          </p>

          <p style={{margin: 0, fontSize: '0.9rem', color: 'rgba(233, 246, 255, 0.82)', textAlign: 'center'}}>
            Já tem conta?{' '}
            <a href="/login" style={{color: '#61f7d2', fontWeight: 600, textDecoration: 'none'}}>
              Voltar ao login
            </a>
          </p>
        </section>

        <aside style={asideStyle}>
          <div>
            <h2 style={{margin: '0 0 12px', fontSize: '1.8rem', fontWeight: 600, color: '#e2f1ff'}}>Plano Free imediato</h2>
            <p style={{margin: 0, color: 'rgba(185, 202, 224, 0.85)', lineHeight: 1.6}}>
              Cadastre-se em instantes e ative o plano Free com Score ATS, monitoramento de vagas e logs em tempo real dos agentes Sentinel.
            </p>
          </div>

          <div style={{display: 'flex', flexDirection: 'column', gap: '14px'}}>
            <div style={{display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 16px', borderRadius: '16px', border: '1px solid rgba(58, 247, 198, 0.28)', background: 'rgba(6, 17, 28, 0.82)', color: 'rgba(165, 243, 252, 0.9)', fontWeight: 600, fontSize: '0.95rem'}}>
              ⚡ Ativação automática do plano Free
            </div>
            <div style={{display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 16px', borderRadius: '16px', border: '1px solid rgba(58, 247, 198, 0.28)', background: 'rgba(6, 17, 28, 0.82)', color: 'rgba(165, 243, 252, 0.9)', fontWeight: 600, fontSize: '0.95rem'}}>
              🔐 Sessão protegida com autenticação Sentinel
            </div>
            <div style={{display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 16px', borderRadius: '16px', border: '1px solid rgba(58, 247, 198, 0.28)', background: 'rgba(6, 17, 28, 0.82)', color: 'rgba(165, 243, 252, 0.9)', fontWeight: 600, fontSize: '0.95rem'}}>
              🛰️ Redirecionamento automático para o dashboard inteligente
            </div>
          </div>

          <p style={{margin: 0, color: 'rgba(148, 163, 184, 0.72)', fontSize: '0.85rem'}}>
            Precisa de suporte? <a href="mailto:contato@sentinel-os.ia.br" style={{color: '#4aa3ff', fontWeight: 600, textDecoration: 'none'}}>Fale com nosso time.</a>
          </p>
        </aside>
      </div>
    </div>
  );
}
