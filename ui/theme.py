from __future__ import annotations

import streamlit as st


def inject_styles() -> None:
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
        <style>
        :root {
          --neutral-0:#11141a;--neutral-50:#151820;--neutral-100:#1c2029;--neutral-200:#292e38;
          --neutral-350:#3b424f;--neutral-400:#858c98;--neutral-600:#aeb4be;--neutral-700:#d2d6dc;
          --neutral-900:#f5f7f9;--red-50:#351b1d;--red-700:#ff9188;--amber-50:#352a16;
          --amber-700:#f0bd65;--green-50:#173024;--green-700:#77d89a;--green-400:#27c45a;
          --accent:#7c6cff;--accent-hover:#8d7fff;--accent-soft:#25223e;--bg:#0d0f14;
          --surface:var(--neutral-0);--raised:#1f242d;--border:var(--neutral-200);
          --muted:var(--neutral-600);--text:var(--neutral-900);
        }
        html,body,[class*="css"]{font-family:Inter,sans-serif}
        body{margin:0;font-feature-settings:"cv11","ss01";-webkit-font-smoothing:antialiased}
        *:focus-visible{outline:2px solid var(--accent)!important;outline-offset:2px}
        .stApp{background:var(--bg);color:var(--text)}
        [data-testid="stSidebar"]{background:var(--neutral-50);border-right:1px solid var(--border);min-width:280px;max-width:280px}
        [data-testid="stSidebar"]>div:first-child{padding:19px 18px 20px}
        [data-testid="stHeader"]{background:rgba(13,15,20,.94);border-bottom:1px solid var(--border)}
        [data-testid="stHeaderActionElements"]{color:var(--neutral-600)}
        .block-container{max-width:1440px;padding:28px 22px 64px}
        h1,h2,h3{color:var(--text);letter-spacing:-.03em;font-weight:600!important}
        h1{font-size:23.5px!important;line-height:30px!important;letter-spacing:-.3px}
        p,label,[data-testid="stCaptionContainer"]{color:var(--muted)}
        .sidebar-brand{display:flex;align-items:center;gap:13px;height:48px;margin-bottom:28px}
        .brand-mark{width:48px;height:48px;border-radius:14px;background:var(--neutral-900);color:var(--bg);display:grid;place-items:center;font-size:18px;font-weight:600;letter-spacing:-.5px;flex:0 0 48px}
        .brand-name{color:var(--text);font-size:16px;line-height:22px;font-weight:600;letter-spacing:-.25px}
        .brand-plan{color:var(--neutral-400);font-size:12.5px;line-height:18px}
        .eyebrow{color:var(--neutral-600);font-size:12px;line-height:16px;font-weight:500;letter-spacing:.5px;text-transform:uppercase;margin-bottom:6px}
        .hero-title{color:var(--text);font-size:31.5px;line-height:38px;font-weight:600;letter-spacing:-.4px;margin:0 0 8px}
        .hero-copy{color:var(--muted);max-width:760px;font-size:14px;line-height:20px}
        .status-row{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 24px}
        .pill{display:inline-flex;align-items:center;gap:7px;min-height:26px;padding:3px 9px;border:1px solid var(--neutral-350);border-radius:7px;background:var(--surface);color:var(--neutral-600);font-size:12px;line-height:18px;font-weight:500}
        .dot{width:8px;height:8px;border-radius:50%;background:var(--green-400)}.dot.off{background:var(--red-700)}
        .metric-card{min-height:111px;border:0;border-left:1px solid var(--border);border-radius:0;padding:18px 18px 14px;background:var(--surface)}
        .metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));border:1px solid var(--border);border-radius:12px;overflow:hidden;background:var(--surface);margin:4px 0 14px}
        .metric-grid .metric-card{border-left:1px solid var(--border);border-bottom:1px solid var(--border)}
        .metric-grid .metric-card:first-child,div[data-testid="column"]:first-child .metric-card{border-left:0}
        .metric-label{color:var(--muted);font-size:14px;line-height:20px;font-weight:400}
        .metric-value{color:var(--text);font-size:31.5px;line-height:38px;letter-spacing:-.4px;font-weight:600;margin:7px 0 3px}
        .metric-note{display:inline-flex;color:var(--neutral-600);background:var(--neutral-50);border-radius:7px;padding:3px 7px;font-size:12px;line-height:18px;font-weight:500}
        .metric-good{color:var(--green-700);background:var(--green-50)}.metric-warn{color:var(--red-700);background:var(--red-50)}
        .panel-kicker{color:var(--neutral-400);font-size:12px;line-height:16px;letter-spacing:.5px;text-transform:uppercase;margin-bottom:4px;font-weight:500}
        .panel-title{color:var(--text);font-size:16px;line-height:22px;font-weight:600;margin-bottom:3px}
        .panel-copy{color:var(--muted);font-size:12.5px;line-height:18px;margin-bottom:14px}
        .journey{display:grid;grid-template-columns:repeat(3,1fr);gap:.8rem;margin:1rem 0}
        .journey-step,.flow-node{border:1px solid var(--border);border-radius:10px;padding:14px;background:var(--neutral-50)}
        .journey-index,.flow-node b{color:var(--neutral-400);font-weight:500;font-size:12px;letter-spacing:.5px;text-transform:uppercase}
        .journey-name{color:var(--text);font-weight:600;margin:5px 0}.journey-copy,.flow-node span{color:var(--muted);font-size:12.5px;line-height:18px}
        .trace-chip{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.72rem;color:var(--neutral-700);background:var(--neutral-50);border:1px solid var(--border);border-radius:7px;padding:6px 8px;word-break:break-all}
        .flow-grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:.55rem}.flow-node{min-height:112px;padding:12px}.flow-node b{display:block;margin-bottom:7px}
        .stButton>button,.stLinkButton>a{border-radius:10px!important;min-height:38px;background:var(--neutral-100);border:1px solid var(--neutral-350);color:var(--neutral-700)!important;font-size:14px;font-weight:500;white-space:nowrap;transition:background-color 120ms ease-out,border-color 120ms ease-out,color 120ms ease-out;box-shadow:none!important}
        .stButton>button p,.stLinkButton>a p,.stButton>button span,.stLinkButton>a span{color:inherit!important}
        .stButton>button:hover,.stLinkButton>a:hover{background:var(--raised);border-color:#596170;color:var(--neutral-900)!important}
        .stButton>button[kind="primary"]{background:var(--accent);border-color:var(--accent);color:#fff!important;box-shadow:0 5px 14px rgba(124,108,255,.22)!important}
        .stButton>button[kind="primary"]:hover{background:var(--accent-hover);border-color:var(--accent-hover)}
        .stButton>button:disabled,.stLinkButton>a[aria-disabled="true"]{background:var(--neutral-100)!important;border-color:var(--neutral-200)!important;color:var(--neutral-400)!important;opacity:.62;cursor:not-allowed}
        [data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--border)!important;background:var(--surface);border-radius:10px;box-shadow:none}
        [data-testid="stDataFrame"]{border:1px solid var(--border);border-radius:10px;overflow:hidden}
        [data-testid="stMetric"]{background:var(--neutral-50);border-radius:10px;padding:10px}[data-testid="stMetricValue"]{color:var(--text);font-size:23.5px;font-weight:600}
        [data-baseweb="input"]>div,[data-baseweb="select"]>div,[data-testid="stChatInput"]{background:var(--neutral-50)!important;border-color:var(--border)!important;border-radius:10px!important}
        [data-testid="stSidebar"] [role="radiogroup"] label{position:relative;min-height:38px;width:100%;padding:0 12px!important;border-radius:10px;gap:0!important}
        [data-testid="stSidebar"] [role="radiogroup"] input,[data-testid="stSidebar"] [role="radiogroup"] label>div:first-child,[data-testid="stSidebar"] [data-baseweb="radio"]>div:first-child{display:none!important}
        [data-testid="stSidebar"] [role="radiogroup"] label:hover{background:var(--neutral-100)}
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){background:var(--accent-soft);box-shadow:0 2px 8px rgba(0,0,0,.24)}
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked)::before{content:"";position:absolute;left:0;top:9px;bottom:9px;width:3px;border-radius:3px;background:var(--accent)}
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p{color:#fff!important}
        [data-testid="stSidebar"] hr{border-color:var(--border)}
        .sidebar-user{margin-top:24px;padding-top:16px;border-top:1px solid var(--border);display:flex;gap:10px;align-items:center}
        .sidebar-avatar{width:38px;height:38px;border-radius:50%;background:var(--neutral-200);color:var(--neutral-700);display:grid;place-items:center;font-size:12px;font-weight:600}
        .sidebar-user b{display:block;color:var(--text);font-size:13px;font-weight:600}.sidebar-user span{color:var(--neutral-400);font-size:11px}
        @media(max-width:1023px){[data-testid="stSidebar"]{min-width:232px;max-width:232px}[data-testid="stSidebar"]>div:first-child{padding-left:14px;padding-right:14px}}
        @media(max-width:767px){[data-testid="stSidebar"]{min-width:0;max-width:280px}.block-container{padding:22px 14px 48px}.journey,.flow-grid{grid-template-columns:1fr}.metric-card{border-left:0;border-bottom:1px solid var(--border)}.metric-grid{grid-template-columns:repeat(auto-fit,minmax(140px,1fr))}}
        </style>
        """,
        unsafe_allow_html=True,
    )
