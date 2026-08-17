from products.sentinel_career.backend.recruiter.analyzer import analyze_profile


def test_recruiter_profile_analysis_returns_text():
    profile = """
    Reginaldo Soares

    Analista de TI | Microsoft 365 | Azure | AWS | Cybersecurity

    Bacharel em Sistemas de Informação.

    Fundador do Sentinel OS.

    Experiência com:
    Microsoft 365
    Azure
    AWS
    Service Desk
    Cybersecurity
    Suporte Técnico
    Cisco Ethical Hacking
    """

    result = analyze_profile(profile)

    assert isinstance(result, str)
    assert result.strip() != ""
