# The Slow Drip — Homepage Design (Magazine · Warm Cream)

> Quyết định 2026-08-28: đổi homepage dripper.top từ theme gradient xanh-tím sang
> **"Editorial Magazine · nền cream ấm"** — hợp vibe du lịch/lifestyle nhưng ấm cho cà phê.
> Nguồn cảm hứng: **Adventure.com** (travel editorial) nhưng **bỏ tông tối + đỏ gắt**, thay bằng cream ấm.

## Vibe mục tiêu
Tạp chí travel/lifestyle ấm — kể chuyện bằng ảnh lớn, chữ sang, thư thái. Không phải blog kỹ thuật.

## Design tokens

### Palette (cream ấm, hợp cà phê)
| Token | Hex | Dùng cho |
|---|---|---|
| `--bg` | `#faf6ef` | nền trang (cream) |
| `--surface` | `#ffffff` | card |
| `--ink` | `#3a2f28` | text chính (nâu cà phê đậm) |
| `--muted` | `#8a7a6a` | text phụ |
| `--accent` | `#b07840` | caramel/copper (link, nút, badge) |
| `--accent-soft` | `#e8dcc9` | chip/tag nền nhạt |
| `--line` | `#e6dccb` | border nhẹ |

### Typography (3 tầng)
- **Display/Tiêu đề:** serif ấm — `"Fraunces"` (hoặc Playfair Display) — headlines, hero, tên bài.
- **Body:** `Inter` (hoặc system sans) — thân bài, dễ đọc.
- **UI/nhỏ:** `Inter` — meta, chips, nút.
- Load: Google Fonts `Fraunces:600,700` + `Inter:400,500,600`.

### Layout (magazine, image-first)
- Hero: bài mới nhất to — ảnh tràn edge-to-edge, tiêu đề serif lớn, excerpt + CTA.
- Section-heading: phân khối theo hạng mục (VD "Vietnamese Coffee" / "Espresso" / "Brewing Guides") — cỡ chữ nhỏ, letter-spacing, có đường gạch.
- Card: media-object (ảnh trái/chữ phải, hoặc ảnh trên/chữ dưới) — ảnh lớn, tiêu đề serif, excerpt, meta (ngày · read time).
- Nhiều whitespace, bo góc vừa phải, bóng rất nhẹ.

### Khác
- Đường dây "Xin chào, mình là..." — giọng bạn bè (personal) ở hero.
- Giữ nguyên CSS `layout-*` (component block) cho bài viết; chỉ đổi giao diện homepage.

## File liên quan
- `ai-blog-automation/scripts/publish.py` → `build_index()` + `INDEX_TEMPLATE` (đây là nguồn sửa).
- Build lại: `PYTHONPATH=src .venv/bin/python scripts/publish.py` (SITE_URL=https://dripper.top).
- Deploy: `publish_cf.py --no-build` với token Pages (cfut_b6...).

## Trạng thái
- [x] Ghi nhận quyết định + design tokens (file này)
- [ ] Dựng `build_index` + `INDEX_TEMPLATE` theo token trên
- [ ] Rebuild + deploy (direct upload) + verify trên dripper.top
