from backend.ats.analyzer import analyze_resume


def test_analyze_resume_returns_json_like_dict():
	resume = """
	Reginaldo Soares

	Bacharel em Sistemas de Informação.

	Experiência em Microsoft 365,
	Azure,
	AWS,
	Service Desk,
	Suporte Técnico,
	Cybersecurity.

	Fundador do Sentinel OS.

	Certificações Cisco:
	Ethical Hacking
	Cybersecurity Essentials
	"""

	result = analyze_resume(resume)

	assert isinstance(result, dict)
	assert "success" in result
	assert "recommendations" in result.get("data", {})
