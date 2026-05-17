"""
email_service.py — Envoi d'emails via Resend (https://resend.com)
Free tier : 3 000 emails/mois, 100/jour
Configuration : ajouter RESEND_API_KEY=re_xxx dans .env
"""
import os
import resend

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FRONTEND_URL   = os.getenv("FRONTEND_URL", "http://localhost:8080")
BACKEND_URL    = os.getenv("BACKEND_URL", "http://localhost:5001")
FROM_EMAIL     = os.getenv("MAIL_FROM", "Carrerlink <onboarding@resend.dev>")


def _build_html(token: str, role: str, prenom: str) -> str:
    role_label  = "Candidat" if role == "user" else "Recruteur"
    verify_link = f"{BACKEND_URL}/auth/verify-email?token={token}"
    color_btn   = "#4f46e5" if role == "user" else "#059669"
    color_grad  = "135deg, #4f46e5, #6366f1" if role == "user" else "135deg, #059669, #10b981"

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <style>
    body {{ margin:0; padding:0; background:#f1f5f9; font-family: 'Inter', Arial, sans-serif; }}
    .outer {{ padding: 40px 20px; }}
    .card {{ max-width:560px; margin:0 auto; background:#fff;
             border-radius:20px; overflow:hidden;
             box-shadow: 0 8px 40px rgba(0,0,0,.12); }}
    .header {{ background: linear-gradient({color_grad});
               padding: 40px 48px 32px; text-align:center; position:relative; }}
    .header .icon {{ width:64px; height:64px; background:rgba(255,255,255,.15);
                     border-radius:16px; display:inline-flex; align-items:center;
                     justify-content:center; font-size:28px; margin-bottom:16px; }}
    .header h1 {{ color:#fff; font-size:1.55rem; font-weight:800;
                  margin:0 0 6px; letter-spacing:-0.5px; }}
    .header p {{ color:rgba(255,255,255,.75); margin:0; font-size:.9rem; }}
    .body {{ padding:40px 48px; }}
    .greeting {{ font-size:1rem; color:#0f172a; font-weight:600; margin-bottom:12px; }}
    .text {{ font-size:.9rem; color:#475569; line-height:1.75; margin-bottom:24px; }}
    .btn-wrap {{ text-align:center; margin:32px 0; }}
    .btn {{ display:inline-block; padding:15px 44px;
            background: linear-gradient({color_grad});
            color:#fff; border-radius:12px; text-decoration:none;
            font-weight:700; font-size:.95rem; letter-spacing:.3px;
            box-shadow: 0 4px 20px rgba(99,102,241,.35); }}
    .note {{ background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px;
             padding:14px 18px; font-size:.78rem; color:#64748b;
             margin-top:20px; line-height:1.6; }}
    .note strong {{ color:#334155; }}
    .link-txt {{ word-break:break-all; color:{color_btn}; font-size:.75rem; margin-top:8px; }}
    .footer {{ border-top:1px solid #f1f5f9; padding:24px 48px;
               text-align:center; font-size:.75rem; color:#94a3b8; }}
    .badge {{ display:inline-block; background:#f1f5f9; color:#64748b;
              border-radius:6px; padding:3px 10px; font-size:.72rem;
              font-weight:600; margin-bottom:16px; }}
  </style>
</head>
<body>
<div class="outer">
  <div class="card">
    <div class="header">
      <div class="icon">✉️</div>
      <h1>Confirmez votre adresse email</h1>
      <p>Vous êtes à une étape de votre espace {role_label}</p>
    </div>
    <div class="body">
      <p class="badge">Carrerlink — Vérification de compte</p>
      <p class="greeting">Bonjour {prenom} 👋</p>
      <p class="text">
        Merci de vous être inscrit en tant que <strong>{role_label}</strong> sur <strong>Carrerlink</strong>,
        la plateforme RH intelligente.<br><br>
        Pour activer votre compte et accéder à toutes les fonctionnalités, veuillez confirmer
        votre adresse email en cliquant sur le bouton ci-dessous.
      </p>
      <div class="btn-wrap">
        <a href="{verify_link}" class="btn">✓ &nbsp;Confirmer mon email</a>
      </div>
      <div class="note">
        <strong>⏱ Ce lien expire dans 1 heure.</strong><br>
        Si vous n'avez pas créé de compte sur Carrerlink, ignorez simplement cet email.<br><br>
        Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :
        <div class="link-txt">{verify_link}</div>
      </div>
    </div>
    <div class="footer">
      © 2026 Carrerlink — Plateforme RH propulsée par Neo4j<br>
      <span style="margin-top:4px;display:block;">Cet email a été envoyé automatiquement, merci de ne pas y répondre.</span>
    </div>
  </div>
</div>
</body>
</html>"""


def send_verification_email(to_email: str, token: str, role: str, prenom: str) -> bool:
    """
    Envoie un email de vérification via l'API Resend.
    Retourne True si succès, False sinon.
    """
    if not RESEND_API_KEY:
        print(f"[EMAIL] RESEND_API_KEY non configuré.")
        print(f"[EMAIL][DEV] Lien de vérification : {BACKEND_URL}/auth/verify-email?token={token}")
        return False

    resend.api_key = RESEND_API_KEY

    try:
        params: resend.Emails.SendParams = {
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": "✅ Confirmez votre inscription — Carrerlink",
            "html": _build_html(token, role, prenom),
        }
        email = resend.Emails.send(params)
        print(f"[EMAIL] Email envoyé via Resend à {to_email} — id: {email.get('id')}")
        return True
    except Exception as e:
        print(f"[EMAIL] Erreur Resend : {e}")
        return False
