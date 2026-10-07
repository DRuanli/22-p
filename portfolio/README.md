# Starter kit — web giới thiệu bản thân (Claude Design → Claude Code cloud)

Bộ khung này đã có sẵn skill, agent, hook, MCP và brief. Bạn chỉ cần đẩy lên GitHub
rồi mở cloud session. Phần mã web (Astro) sẽ do Claude Code dựng ở bước 4.

## Có gì trong repo

| Đường dẫn | Vai trò |
|---|---|
| `CLAUDE.md` | Brief dự án: stack, map các section theo trang tham khảo, luật motion, tiêu chí "xong" |
| `.claude/skills/frontend-design` | Skill chính thức của Anthropic: tránh giao diện "AI generic" (Apache-2.0) |
| `.claude/skills/gsap-*` (8 skill) | Skill chính thức của GreenSock: core, timeline, ScrollTrigger, plugins (SplitText), performance… (MIT) |
| `.claude/skills/webapp-testing` | Skill Playwright của Anthropic: chạy server, chụp màn hình, đọc log |
| `.claude/skills/reference-motion` | Skill viết riêng cho dự án: công thức hero, reveal tiêu đề, parallax, card rail, carousel, accordion |
| `.claude/agents/visual-qa.md` | Subagent kiểm tra giao diện ở 375/768/1280/1440px + reduced-motion, trả danh sách lỗi |
| `.claude/settings.json` + `scripts/session-start.sh` | Hook tự `npm ci` + cài Chromium khi cloud session khởi động |
| `.mcp.json` | MCP Playwright (Claude tự mở trình duyệt xem trang) + Context7 (tra docs mới nhất của Astro/GSAP/Lenis) |
| `scripts/shots.mjs` | Chụp full-page ở 4 kích thước, báo lỗi console và tràn ngang |
| `docs/content.md` | **Nội dung thật của bạn** — điền các dòng TODO |
| `docs/claude-design-brief.md` | Brief dán vào Claude Design |
| `docs/reference/` | Bỏ ảnh chụp màn hình trang tham khảo vào đây |

Vì sao skill nằm trong repo: cloud session **không cài plugin** (`/plugin` không chạy ở cloud,
và `enabledPlugins` trong settings.json bị bỏ qua) — chỉ những gì commit trong `.claude/`
mới được nạp. Skill bạn bật trên claude.ai cũng được nạp tự động.

## Các bước

**1. Chuẩn bị (máy của bạn, ~15 phút)**
- Điền `docs/content.md`.
- Chụp 4–6 ảnh trang tour-kyrgyzstan.com (hero, khối founder, rail tour, FAQ) ở bản
  desktop và mobile, lưu vào `docs/reference/` (ví dụ `01-hero-1440.png`). Quay thêm 1
  đoạn video cuộn trang để dùng cho Claude Design.
- Chuẩn bị video hero của chính bạn (10–20 giây, ≤ 4 MB) và ảnh chân dung.

**2. GitHub + môi trường cloud**
- Tạo repo GitHub (ví dụ `<username>.github.io`), đẩy toàn bộ thư mục này lên.
- Vào claude.ai/code → kết nối GitHub (cài Claude GitHub App cho repo).
- Sửa environment: Network access = **Custom**, tick "Also include default list", thêm:
  ```
  cdn.playwright.dev
  playwright.download.prss.microsoft.com
  mcp.context7.com
  tour-kyrgyzstan.com
  *.framerusercontent.com
  ```
  (npm và Google Fonts đã có sẵn trong danh sách Trusted.)
- GitHub repo → Settings → Pages → Source = **GitHub Actions**.

**3. Claude Design (tuỳ chọn nhưng nên làm)**
- Mở claude.ai/design, dán `docs/claude-design-brief.md`, đính kèm ảnh + video tham khảo.
- Chỉnh tới khi ưng, rồi Export → **Handoff to Claude Code** → chọn Claude Code Web và repo này.

**4. Prompt đầu tiên trong cloud session**
```
Đọc CLAUDE.md, docs/content.md, docs/reference/*.png (và bundle Claude Design nếu có).
Dùng skill frontend-design để lập design plan (palette, type, layout ASCII, motion) vào
docs/plan.md và dừng lại cho mình duyệt. Chưa viết code.
```
Sau khi duyệt:
```
Scaffold Astro theo CLAUDE.md, thêm script "shots": "node scripts/shots.mjs" và
playwright vào devDependencies, rồi build từng section theo plan, mỗi section một commit.
Dùng skill reference-motion và gsap-*. Sau mỗi 2 section chạy agent visual-qa và sửa lỗi.
```

**5. Deploy**: tạo PR từ session → merge vào `main` → GitHub Actions tự build và đăng lên Pages.

## Tiết kiệm credit
- Duyệt plan trước khi cho code (bước 4) — sửa plan rẻ hơn sửa code nhiều.
- Một session dài cho cả dự án thay vì nhiều session ngắn (cache rẻ hơn ~20 lần).
- Việc nhỏ (sửa chữ, màu) → `/model sonnet`; dựng motion phức tạp → model mạnh nhất.
- Giao chụp/so sánh ảnh cho agent `visual-qa` để giữ context chính gọn.

## Bản quyền
Chỉ học bố cục và ngôn ngữ chuyển động của trang tham khảo. Không dùng lại chữ, ảnh,
video, logo của họ; logo trường/tạp chí thay bằng chữ; trích dẫn chỉ dùng câu thật, có xin phép.
