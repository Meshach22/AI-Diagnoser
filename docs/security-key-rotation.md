# Provider Security & API Key Rotation Checklist

> [!IMPORTANT]
> The repository cleanup cannot revoke provider credentials.
> Provider keys must be revoked through their respective provider dashboards or authenticated provider APIs.
> Any credentials previously committed or exposed should be considered permanently compromised and replaced immediately.

---

## 1. Google Gemini (Google AI Studio)

- [ ] Revoke old Gemini key (Google AI Studio dashboard -> API keys -> Revoke)
- [ ] Create new Gemini key
- [ ] Add new Gemini key to local `.env`:
  ```bash
  GEMINI_API_KEY="your-new-gemini-key-here"
  ```
- [ ] Verify Gemini request via API or Streamlit UI

---

## 2. OpenAI

- [ ] Revoke old OpenAI key (OpenAI Platform -> API keys -> Revoke)
- [ ] Create new OpenAI key
- [ ] Add new OpenAI key to local `.env`:
  ```bash
  OPENAI_API_KEY="your-new-openai-key-here"
  ```
- [ ] Verify OpenAI request via API or Streamlit UI

---

## 3. Groq Cloud

- [ ] Revoke old Groq key (Groq Console -> API Keys -> Delete)
- [ ] Create new Groq key
- [ ] Add new Groq key to local `.env`:
  ```bash
  GROQ_API_KEY="your-new-groq-key-here"
  ```
- [ ] Verify Groq request via API or Streamlit UI

---

## 4. DeepSeek

- [ ] Revoke old DeepSeek key (DeepSeek Platform -> API Keys -> Delete)
- [ ] Create new DeepSeek key
- [ ] Add new DeepSeek key to local `.env`:
  ```bash
  DEEPSEEK_API_KEY="your-new-deepseek-key-here"
  ```
- [ ] Verify DeepSeek request via API or Streamlit UI

---

## 5. Local `.env` Verification

- [ ] Verify `.env` is NOT tracked by Git:
  ```bash
  git check-ignore .env
  git ls-files .env
  ```
- [ ] Ensure `.env.example` contains only placeholder strings (`""`)
