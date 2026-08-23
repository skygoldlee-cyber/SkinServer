# ?Œì¼ ?ˆë‚´ (MANIFEST) ??monorepo ?„ì²´ ?Œì¼ ?¤ëª…

> SkinLens **monorepo**??ì£¼ìš” ?Œì¼???´ë”ë³„ë¡œ ?˜ë‚˜???¤ëª…?˜ëŠ” ì¹´íƒˆë¡œê·¸?…ë‹ˆ??
> "ë¬´ì—‡ë¶€???½ì„ì§€"(?½ëŠ” ?œì„œ)??[`./README.md`](./README.md), "ê°??Œì¼??ë¬´ì—‡?¸ì?"(?„ì²´ ëª©ë¡)????ë¬¸ì„œ?…ë‹ˆ??
> ê²½ë¡œ??**?€?¥ì†Œ ë£¨íŠ¸ ê¸°ì?**?…ë‹ˆ?? ??ë¬¸ì„œ?¸íŠ¸ ???„ì¬ ê²½ë¡œ???•ë³¸ ?€?‘í‘œ??[`../MIGRATION.md`](../MIGRATION.md).
> ?„ì¬ êµ¬ì¡°??**3-Tier(Vercel Â· Supabase Â· AI Server)** ë¡??¬í¸ ì¤‘ì…?ˆë‹¤.

## ?´ë” ?œëˆˆ??

| ?´ë” | ?±ê²© |
|---|---|
| (ë£¨íŠ¸) | ?€?¥ì†Œ ?ˆë‚´Â·ê³µí†µ ?¤ì •(MakeÂ·pytestÂ·?˜ê²½ ?ˆì‹œ) |
| `docs/` | ?¤ê³„Â·?´ì˜ ë¬¸ì„œ(ì½”ë“œ?€ ë¶„ë¦¬) ??storiesÂ·server-setupÂ·architectureÂ·operationsÂ·roadmapÂ·reviewÂ·integration |
| `services/` | AI Server ë°±ì—”?? gateway Â· worker Â· engine-analysis Â· engine-prescription |
| `apps/` | ?„ë¡ ???œë©´: webapp-next(Next.js PWA) Â· webapp(?ˆê±°??Vite) Â· homepage Â· devpage |
| `packages/` | ?œë¹„??ê³µìš© ì½”ë“œ(ê³„ì•½Â·ê·œê²©) |
| `deploy/` | AI Server ë°°í¬ ?¤íƒ(?¸í”„??: compose Â· caddy Â· scripts Â· supabase Â· ops-jobs Â· db Â· nginx(?ˆê±°?? |
| `.github/workflows/` | CI/CD(AI Server ?„ìš© ???¹ì? Vercel ?ë™) |
| `tests/` | ?µí•©Â·?¤ëª¨??pytest) |
| `site/` | ë¬¸ì„œ ?¬í„¸(`index.html`) |

---

## (ë£¨íŠ¸)

| ?Œì¼ | ?¤ëª… |
|---|---|
| `README.md` | **?€?¥ì†Œ ê°œìš”.** monorepo êµ¬ì¡°Â·3-Tier ?„í‚¤?ì²˜ ?œëˆˆ?Â·ë°°???¤íƒ ?”ì•½. |
| `MIGRATION.md` | **??ë¬¸ì„œ?¸íŠ¸(`SkinServer`) ???„ì¬ ê²½ë¡œ ?•ë³¸ ?€?‘í‘œ** + compose ?µí•© ?ì„¸ + ?¨ì? ?˜ì‘?? |
| `Makefile` | ?¨ì¶• ëª…ë ¹ ??`deploy/scripts/sl`???‡ì? ?˜í¼(`make dev-up` ?? + **?”ë“œ?¬ì—”???¤ëª¨??*(?…ë¡œ?œâ†’job_id?’ìƒ???´ë¦¬) + pytest ?€ê²? |
| `pytest.ini` | pytest ?¤ì •(?ŒìŠ¤??ê²½ë¡œÂ·ë§ˆì»¤). |
| `requirements-dev.txt` | ê°œë°œ/?ŒìŠ¤??ê³µí†µ ?˜ì¡´?? |
| `.env.example` | ë£¨íŠ¸ ê°œë°œ???˜ê²½ ?ˆì‹œ(?œë¹„??URL ??. |
| `.gitignore` | `.env`Â·`.env.images`Â·`__pycache__`Â·?•ì  ?¤ì½˜?ì¸  ???œì™¸. |

## `docs/` ??ë¬¸ì„œ

### `docs/`(?¸ë±??

| ?Œì¼ | ?¤ëª… |
|---|---|
| `docs/README.md` | **?½ëŠ” ?œì„œÂ·ê´€ê³„ë„.** ?„ì¬ docs êµ¬ì¡° + ??ë²ˆí˜¸?’í˜„???„ì¹˜ + 3-Tier ?´ì „ ì¶?+ ?í™©ë³??¼ìš°?? |
| `docs/MANIFEST.md` | **??ë¬¸ì„œ.** ëª¨ë“  ?Œì¼???•ì²´ë¥??´ë”ë³„ë¡œ ??ì¤„ì”© ?¤ëª…?˜ëŠ” ì¹´íƒˆë¡œê·¸. |
| `docs/outsourcing/skinlens_outsourcing_srs.md` | **?¸ì£¼ê°œë°œ ?”êµ¬?¬ì–‘ ëª…ì„¸??(SRS).** ?…ë ¥ ?°ì´??ê²€ì¦? Worker ?¥ì•  ?€?? AI/ì²˜ë°© ?”ì§„ ê³ ë„??ë°?ë³´ì•ˆ/?´ì˜ ?”ê±´ ?•ì˜. |
| `docs/outsourcing/HANDOFF_?¸ì£¼ê°œë°œ??md` | **?¸ì£¼ê°œë°œ???¸ë„ ë¬¸ì„œ ?¨í‚¤ì§€.** SRS ?¸ì— ?„ë‹¬??ë¬¸ì„œë¥?ëª©ì ë³?? ì„¤ê³??•ë³¸Â·?‘ì—… ë²”ìœ„ ?¡APIÂ·?°ì´??ê³„ì•½ ??—”ì§??„ë©”???£ì‹¤?‰Â·ê?ì¦??˜ê²½ ?¤ì½”???ˆì§ˆ ê¸°ì????¥ë¹„ê¸°ìˆ  ë°°ê²½)ë¡?ë¬¶ê³  ?„ë‹¬ ?´ìœ Â·ê¶Œì¥ ?„ë‹¬ ë°©ì‹Â·?¸ë„ ì²´í¬ë¦¬ìŠ¤??ëª…ì‹œ. |
| `docs/deploy_components_guide.md` | **?µí•© ë°°í¬ ?¤íƒ (deploy/) êµ¬ì„± ?”ì†Œ ê°€?´ë“œ.** Docker compose, Caddy, ?¤í¬ë¦½íŠ¸, DB ë§ˆì´ê·¸ë ˆ?´ì…˜ ë°?RLS ??deploy ?´ë” ??ëª¨ë“  ?Œì¼???ì„¸ ??•  ê¸°ìˆ . |

### `docs/stories/` ??ê°œë… ?”ì•½ (?´ì•¼ê¸°ì²´)

| ?Œì¼ | ?¤ëª… |
|---|---|
| `docs/stories/README.md` | **?ˆë¸Œ(ë¨¼ì? ?½ê¸°).** ?½ëŠ” ?œì„œ Â· ê³µìš© **ë¹„ìœ  ?¬ì „**(ì°½ê³  ?©ì–´ ?µì¼) Â· ?¬í™”??ë¡œë“œë§?+ ?›â†’?„ì¬ ê²½ë¡œ ë§¤í•‘. |
| `docs/stories/01_SkinLens_?œë²„_?´ì•¼ê¸?md` | ?„ì²´ ?¬ì •??"?‘ì? ?ë‹¹"?¼ë¡œ ??**overview**(6ë§?+ ë§?0-B ì£¼ë¬¸ ì²˜ë¦¬: ?¬ì§„+?¤ë¬¸ ?…ë¡œ?œâ†’ë¶„ì„?’ì²˜ë°?. |
| `docs/stories/02_SkinLens_êµ¬ì¶•_?´ì•¼ê¸?md` | êµ¬ì¶• **?¬í™”**: ë¹??…â†’ê²€ì¦ëœ ì£¼ë°©(ê³¨ì¡°Â·SSHÂ·?¤ì¤‘ ê³„ì •Â·DockerÂ·?¤íŠ¸?Œí‚¹Â·ê²€ì¦?. |
| `docs/stories/03_SkinLens_?˜ë“œ???´ì•¼ê¸?md` | ?˜ë“œ??**?¬í™”**: ?´ë¦° ì£¼ë°©?’ì ê¸?ì£¼ë°©(ë¬¸ì?ê¸°Â·SSHÂ·?·ë¬¸Â·nginx ?œë©´Â·ì»¨í…Œ?´ë„ˆÂ·?”ì§„ ê³¨ë°©). |
| `docs/stories/04_SkinLens_?´ì˜_?´ì•¼ê¸?md` | ?´ì˜ **?¬í™”**: ?ë™ ê°œì (restart ?•ì±…), ?œê³„ ?™ê¸°?? ë¡œê·¸/?€???í•œ ì²?†Œ, ?ë™ ?¨ì¹˜, ?ê²© ëª¨ë‹ˆ?°ë§Â·?œì–´(ë¬´ì „ê¸? ë°??Œë¦¼(uptime-kuma) êµ¬ì¡° ?¤ëª…. |
| `docs/stories/05_SkinLens_ë°±ì—…_?´ì•¼ê¸?md` | ë°±ì—… **?¬í™”**: ?°ì´?°ë² ?´ìŠ¤ ?¼ë¦¬ ë°±ì—…, AES-256 ?”í˜¸?? ?¤í”„?¬ì´???„ì†¡, ë³´ì¡´ ?°í•œ, ?°ë“œë§??¤ìœ„ì¹?ê²½ë³´ ë°?ë³µêµ¬ ë¦¬í—ˆ??ëª¨ì˜ ?ˆë ¨. |
| `docs/stories/06_SkinLens_?´ê?_?´ì•¼ê¸?md` | ?´ê? **?¬í™”**: ì§?ì£¼ë°©?’ì˜?…ì (DNS TTLÂ·?ê? ëª¨ë“œÂ·?¸í? ?¤í”„Â·verify prodÂ·?„í™˜Â·ë¡¤ë°±). |
| `docs/stories/07_SkinLens_ë°°í¬_?´ì•¼ê¸?md` | ë°°í¬ **?¬í™”**: ì½”ë“œ ??ì¤„ì´ ?ë‹˜?ê¹Œì§€(?•ì Â·?œë²„ë¹Œë“œÂ·?”ì§„ ???¬ì •, ?¤í…Œ?´ì§•/?´ì˜). |
| `docs/stories/08_SkinLens_ê¸°ë™_?´ì•¼ê¸?md` | ê¸°ë™ **?¬í™”**: ?˜ê²½ë³?ë¹Œë“œÂ·ê¸°ë™ ?ˆì°¨ë¥?"ê°™ì? ë°°ì¹˜?? ?¤ë¥¸ ë©”ëª¨"ë¡?dev ì¡°ë¦¬ / staging ?„ì œ??/ prod ì°½ê³ +?ë¬¼??. ?¤ë¬´ ì§„ì…?ì? `deploy/scripts/sl`. |
| `docs/stories/09_SkinLens_3Tier_?´ì „_?´ì•¼ê¸?md` | **3-Tier ?´ì „ ?¬í™”**: ì§?ì£¼ë°© ê°„íŒ ?¼ê³  ?„ë¬¸???‹ìœ¼ë¡?Vercel ?¼ìœˆ?„Â·Supabase ì°½ê³ Â·AI Server ì£¼ë°©). |
| `docs/changelog/stories_ë³€ê²½ìš”??md` | ?´ì•¼ê¸?ë³€ê²??´ì—­(v2 ?©ì–´ ?µì¼ ??v3 ê²½ë¡œ ê°±ì‹  ??v3.1 ë¹„ìœ  ?•í•©?±Â·ì‹¬?”í¸ ?•ì¥). |

### `docs/server-setup/` ??ê¸°ë°˜ (ë²”ìš© ?œë²„ êµ¬ì¶•)

| ?Œì¼ | ?¤ëª… |
|---|---|
| `docs/server-setup/windows11_ubuntu_server_setup.md` | **ì¤‘ì‹¬ ê°€ì´ë“œ.** Windows 11 ìƒ WSL2 Ubuntu ì„œë²„ êµ¬ì¶•(0~27ì¥)Â·í•˜ë“œë‹Â·ìš´ì˜Â·ë°±ì—…. v3 ë°˜ì˜. |
| `docs/server-setup/Vercel_Render_ê¸°ë°˜_ì›¹ì„œë¹„ìŠ¤_ë„ë©”ì¸_IP_êµ¬ì„±_ê°€ì´ë“œ_ìˆ˜ì •ë³¸.md` | **ë„ë©”ì¸ & IP ê°€ì´ë“œ.** Vercel + Render 3-Tier ê¸°ë°˜ ì›¹ì„œë¹„ìŠ¤ ë„ë©”ì¸ ë° IP êµ¬ì„± ê°€ì´ë“œ (í˜„í–‰ ê¶Œì¥). |
| `docs/server-setup/server_migration_runbook.md` | ì™¸ë¶€ ì„œë²„(VPS/í´ë¼ìš°ë“œ) **ì´ê´€** ëŸ°ë¶ (ë ˆê±°ì‹œ ìì²´ ì„œë²„ VPS ì´ê´€ ì‹œ ì°¸ê³ ìš©). |
| `docs/changelog/server-setup_ê²€ì¦ë³´ê°??¸íŠ¸.md` | ê²€ì¦?ë³´ê°• 3ê°€ì§€(?˜ë“œ??ëª¨ë“ˆÂ·ê²Œì´???°ì¥Â·verify_ops) ?”ì•½. |
| `docs/changelog/server-setup_ë³´ì™„ê°œì„ _v2_?¸íŠ¸.md` | 2ì°?ë³´ì™„(ufw?”DockerÂ·?¬íŠ¸ ?¸ì¶œÂ·WSL ?˜ëª…ì£¼ê¸° ??6ê°€ì§€) ë¦¬ë·°. |
| `docs/changelog/server-setup_ë³´ì™„ê°œì„ _v3_?¸íŠ¸.md` | 3ì°?ë³´ì™„(?½ì•„??ë°©ì?Â·?¤ëƒ…?·Â·ë°±??ê²¬ê³ ?±Â·ì»¨?Œì´???˜ë“œ?Â·ì»·?¤ë²„ ?•í•©????11ê°€ì§€) ë¦¬ë·°. |
| `docs/server-setup/changes/CHANGES{,_v2,_v3}.diff` | 1Â·2Â·3ì°??¨ì¹˜ ë³€ê²??´ë ¥(`patch -p1` ?¬ì ??ê°€??. |

> ??ê°€?´ë“œê°€ ì°¸ì¡°?˜ëŠ” **?¤í¬ë¦½íŠ¸??`deploy/scripts/`**, **?µí•© ê²€ì¦?pytest)?€ `tests/test_environment.py`** ë¡??´ë™?ˆìŠµ?ˆë‹¤.

### `docs/architecture/` ???¤ë¦¬(?í•©?? + ê°ì‚¬ + 3-Tier ?¤ê³„

| ?Œì¼ | ?¤ëª… |
|---|---|
| `docs/architecture/SkinLens_?œë²„êµ¬ì„±_?í•©??ê²€??md` | ë²”ìš© ê°€?´ë“œê°€ **4?œë©´(?ˆÂ·ê°œë°œìÂ·??PWA)Â·API)+?”ì§„ 2ê°?Supabase**??ë§ëŠ”ì§€ Â§0~9 ?ë‹¨ + ë¶€ë¡?A/B/C(ê¸°ì? ?¤íƒÂ·ëª©í‘œ ? í´ë¡œì?Â·ë¹„ë™ê¸?Job ?ì• ì£¼ê¸°). |
| `docs/architecture/00_README.md` | ê°ì‚¬ ê³„ì¸µ ?´ë” ?ˆë‚´ + ë°°ì„  ë°˜ì˜ ?”ì•½. |
| `docs/architecture/01_SkinLens_?´ì˜?„í‚¤?ì²˜_ìµœì¢…ë¦¬ë·°.md` | ? êµ¬ì¡??¡ë³´????¥???£ê°œ???¤P0/P1/P2. |
| `docs/architecture/02_PATCH_NOTES_P0_P1.md` | ë¬´ì—‡?„Â·ì–´?”ì— ë°˜ì˜ + ?ìš© ?œì„œÂ·ê²€ì¦? |
| `docs/architecture/03_DB_MIGRATION_ROLLBACK.md` | "ì½”ë“œ ë¡¤ë°± ???¤í‚¤ë§?ë¡¤ë°±" ?°ë¶(expand-contract). |
| `docs/architecture/04_3Tier_Vercel_Supabase_AIServer_?¤ê³„.md` | **3-Tier ?¬í¸ ?¤ê³„ ?•ë³¸.** VercelÂ·SupabaseÂ·AI Server 3ë¶„í• ????ë¬´ì—‡?? |
| `docs/architecture/05_3Tier_?´ì „_?‘ì—…ê³„íš.md` | **3-Tier ?´ì „ ?‘ì—…ê³„íš.** Phase 1~6ë³?ë¬´ì—‡?„Â·ì–´???Œì¼?„Â·ì–´???œì„œë¡?+ ?íƒœ ?¤ëƒ…?? |
| `docs/architecture/?”ì§„_baseline_êµì²´_ê°€?´ë“œ.md` | ?”ì§„ baseline(OpenCV/ê·œì¹™) ??ML/GAN êµì²´ ì§€??ê°€?´ë“œ. |

### `docs/operations/` ???´ì˜

| ?Œì¼ | ?¤ëª… |
|---|---|
| `docs/operations/06_?´ì˜Â·ë°°í¬_ì²´í¬ë¦¬ìŠ¤??md` | êµ¬ì¶• ?´í›„ ë°°í¬Â·?´ì˜Â·?˜ë“œ?Â·ë°±?…Â·ì´ê´€???¸ë? ë¬¸ì„œ ?µì»¤ê¹Œì? ê±?ì²´í¬ë¦¬ìŠ¤?? |
| `docs/operations/07_?™ìŠµ_ë¡œë“œë§?md` | ?™ìŠµ ?˜ì¡´???œì„œ(?°ê·¸ë¦¼â†’ë²”ìš©?œë²„?’íŠ¹?”â†’?´ì˜Â·ë°±ì—…?’ì´ê´€?’CD). ?¨ê³„ë³?? ìˆ˜ì§€?Â·ì™„ë£?ê¸°ì?. |
| `docs/operations/?œë²„_?¤í–‰_?´ì˜_ê°€?´ë“œ.md` | ?¤ì œ ?¤í–‰/?´ì˜ ?ˆì°¨(ê¸°ë™Â·?íƒœ ?•ì¸Â·?¼ìƒ ?´ì˜). ê¸°ë™ ëª…ë ¹?€ `sl` ê¸°ì?. |
| `docs/operations/?˜ê²½ë³?ë¹Œë“œ_ê¸°ë™_?ˆì°¨.md` | **?˜ê²½ë³?ë¹Œë“œÂ·ê¸°ë™ ?ˆì°¨ ?•ë³¸.** dev/staging/prod ë¹„êµ ??+ `sl` ?¬ìš©ë²?ì´ˆê¸° ?¤ì • `init`Â·?ê?ì§„ë‹¨ `doctor` ?¬í•¨). ê¸?compose one-liner??ë¶€ë¡? |
| `docs/operations/?Œì´?„ë¼??ì²´í¬?¬ì¸???¸ëŸ¬ë¸”ìŠˆ??md` | ?…ë¡œ?œâ†’ë¶„ì„?’ì²˜ë°??Œì´?„ë¼???¨ê³„ë³?ì²´í¬?¬ì¸?¸Â·ì¥??ì§„ë‹¨. |
| `docs/operations/09_Phase1_Supabase_?¤í–‰?°ë¶.md` | **Phase 1 ?¤í–‰ ?°ë¶.** Supabase ?„ë¡œ?íŠ¸ ?ì„±Â·?¤í‚¤ë§?ë§ˆì´ê·¸ë ˆ?´ì…˜Â·RLS/Storage ?•ì±… ?ìš©Â·`.env` ì±„ìš°ê¸? |
| `docs/operations/10_Phase5_ë°°í¬?œì„œ_?°ë¶.md` | **Phase 5 ?¤í–‰ ?°ë¶.** Vercel/AI Server ë°°í¬ ?œì„œ(ê³„ì•½ ë²„ì „ ê²Œì´??. |
| `docs/operations/11_?ê²©_ëª¨ë‹ˆ?°ë§_?œì–´.md` | **Windows ??Linux ?ê²© ?´ì˜.** SSH ê²½ìœ ë¡??œë²„ ?íƒœ ëª¨ë‹ˆ?°ë§(status/ps/logs/health) + ?œì–´(up/down/restart/deploy) + ê´€ë¦¬í¬???°ë„ë§? `remote.ps1`/`remote.cmd` ?¬ìš©ë²? |

### `docs/roadmap/` ???„ì†

| ?Œì¼ | ?¤ëª… |
|---|---|
| `docs/roadmap/00_PHASE_ROADMAP.md` | **Phase ?¼ë²¨ ??êµ¬í˜„ ?°ì„ ?œìœ„ ???„ì¬ ë°˜ì˜ ?íƒœ** ë§¤í•‘(?¤ë¥¸ ë¬¸ì„œ??"Phase N" ì°¸ì¡° ?´ì†Œ). 3-Tier ?´ì „ ?¸ë™ ?íƒœ ?¤ëƒ…???¬í•¨. |
| `docs/roadmap/09_êµ¬í˜„?°ì„ ?œìœ„_ë°°í¬êµ¬ì¡°_ë¦¬ìŠ¤?¬ì •ë¦?md` | êµ¬í˜„ ?°ì„ ?œìœ„Â·ë°°í¬ êµ¬ì¡°Â·ë¦¬ìŠ¤???•ë¦¬. |
| `docs/roadmap/04_?„ì†ë³´ì™„_ë¡œë“œë§?md` | ì£¼ì œë³?ë°±ë¡œê·?+ ?°ì„  3ê°?ë°˜ì˜ ?„ì¹˜Â·ê¶Œì¥ ?œì„œ. |
| `docs/roadmap/05_ë³´ì™„??ª©_?•ë¦¬.md` | **?ê²© ëª¨ë‹ˆ?°ë§Â·?œì–´ ?´ì™¸???¨ì? ë³´ì™„??ª© ?•ë¦¬.** ?„ë©”?¸ë³„(Aê´€ì¸¡ì„±Â·B?ŒìŠ¤?¸ê²Œ?´íŠ¸Â·C DRÂ·Dê°œì¸?•ë³´Â·Eë¯¸ê²°ê²°ì •Â·Fë¬¸ì„œ) ë¯¸ì™„ ??ª© + ê¶Œì¥ ?°ì„ ?œìœ„. |
| `docs/changelog/ë³´ì™„ë°˜ì˜_?”ì•½.md` | ë³´ì™„ ë°˜ì˜ ?”ì•½(ë¬´ì—‡???´ë””??. |
| `docs/roadmap/engine_advancement_roadmap.md` | **?¼ë?ë¶„ì„ ë°?ì²˜ë°©???”ì§„ ê³ ë„??ë¡œë“œë§?** Heuristic ?œë‹, ?¥ëŸ¬???µí•©, ?¼ë“œë°?ë£¨í”„ ?ê? ì¡°ì • ?¨ê³„ë³??„ëµê³?êµ¬ì²´?ì¸ ì½”ë“œ êµì²´ ì§€??ë°??¤í–‰ ?¡ì…˜ ?Œëœ ?œì‹œ. |

### `docs/review/` ??ì½”ë“œ ë¦¬ë·°

| ?Œì¼ | ?¤ëª… |
|---|---|
| `docs/review/archive/REVIEW_FINDINGS_2026-08-18.md` | **1ì°??„ìˆ˜ ë¦¬ë·°(2026-08-18).** P0/P1/P2 ì§€??+ ê·¼ê±° ë§í¬. (2ì°?ê²€?˜ë¡œ ê³„ìŠ¹Â·ë³´ê?) |
| `docs/review/REVIEW_FINDINGS_2026-08-19.md` | **2ì°?ê²€??2026-08-19).** 1ì°?ì§€???´ê²° ?¬ë? ê²€ì¦?+ ? ê·œ ?´ìŠˆ(N1~N5). |
| `docs/review/RESOLUTIONS_2026-08-19.md` | **?´ê²° ê¸°ë¡(2026-08-19 ?„ì†).** P1-1Â·P1-2Â·P2-1Â·P2-2Â·N1Â·N2Â·N4 ë°˜ì˜ ?´ì—­ + ê²€ì¦? |

### `docs/integration/` ???°ë™

| ?Œì¼ | ?¤ëª… |
|---|---|
| `docs/integration/flutter_app_contract.md` | **Flutter ?????œë²„ ê³„ì•½.** ?¬ì§„+?¤ë¬¸ ???”ì²­(`POST /analyze`)Â·?¤ë¬¸ shapeÂ·?´ë¦¬Â·?¤ë¥˜ ì½”ë“œÂ·Dart ?ˆì‹œ. |

### `docs/changelog/` ???„ë£Œ??ë³€ê²½Â·ë³´???´ë ¥ (?½ê¸° ?„ìš© ë³´ê?)

?„ë£Œ???‘ì—…??"ë¬´ì—‡???´ë””??ë°˜ì˜?ˆë‚˜" ê¸°ë¡. ?„ì¬ ì§€ì¹¨ì´ ?„ë‹ˆ??**?´ë ¥**?´ë?ë¡? ìµœì‹  ?íƒœ???ë¬¸???¤ê³„Â·?°ë¶Â·ë¦¬ë·°)ë¥?ë³¸ë‹¤.

| ?Œì¼ | ?¤ëª… |
|---|---|
| `docs/changelog/ë³´ì™„ë°˜ì˜_?”ì•½.md` | ì½”ë“œ 4ê°??ì—­(?´ì˜?ˆì •?±Â·ì •?•ì„±Â·ê´€ì¸¡Â·ë„ë©”ì¸) ë³´ì™„ ?ìš© ?„ì¹˜. |
| `docs/changelog/stories_ë³€ê²½ìš”??md` | ?´ì•¼ê¸°ì²´ ë¬¸ì„œ v2?’v3?’v3.1 ë°˜ì˜ ?´ì—­. |
| `docs/changelog/server-setup_ë³´ì™„ê°œì„ _v2_?¸íŠ¸.md` Â· `_v3_?¸íŠ¸.md` Â· `_ê²€ì¦ë³´ê°??¸íŠ¸.md` | ?œë²„?‹ì—… 2ì°¨Â?ì°?ë³´ì™„ ë¦¬ë·° + ê²€ì¦?ë³´ê°• ?”ì•½. |

## `services/` ??AI Server ë°±ì—”??

?ì‡„ë§??”ì§„ 2ê°?+ ì£¼ë°©(gateway/worker). ê³µìš© ê³„ì•½?€ `packages/common/skinlens_contract`.

| ?Œì¼ | ?¤ëª… |
|---|---|
| `services/gateway/app/main.py` | **ê²Œì´?¸ì›¨??FastAPI)** ???¨ì¼ ?°ê¸° ì£¼ì²´Â·?¸ì¦ ê²½ê³„. presigned ë°œê¸‰Â·Job ?±ë¡Â·?íƒœ/ë¦¬í¬??ì¡°íšŒ. |
| `services/gateway/app/storage.py` | ?¤í† ë¦¬ì? ì¶”ìƒ??supabase) ??`SupabaseStorage` ?¤êµ¬??presigned ë°œê¸‰/?œëª… URL). |
| `services/gateway/app/logging_setup.py` | êµ¬ì¡°??JSON ë¡œê¹…(job_id ?ê?ID). |
| `services/gateway/{Dockerfile,requirements.txt}` | ê²Œì´?¸ì›¨???´ë?ì§€(ë¹„ë£¨??Â·?˜ì¡´?? |
| `services/worker/worker.py` | **ë¦¬í¬???Œì»¤** ?????Œë¹„Â·?¬ì‹œ??ë¦¬í¼Â·?¨ê³„ ê´€ì¸? ë¶„ì„(?¬ì§„)?’ì²˜ë°?ë¶„ì„ì§€???¤ë¬¸ ë³‘í•©) ?¸ì¶œ ??ê²°ê³¼ ê¸°ë¡. DB ì»¤ë„¥???€(`psycopg-pool`)Â·?„ì‹œ?Œì¼ ?•ë¦¬(`finally`). |
| `services/worker/storage.py` / `logging_setup.py` | ?¤í† ë¦¬ì? ì¶”ìƒ???œëª… URL fetchÂ·magic-byte ?¬ê?ì¦Â·ìŠ¤?¸ë¦¬ë°?`MAX_DOWNLOAD_BYTES` ?í•œÂ·`is_temp` ?„ì‹œ?Œì¼ êµ¬ë¶„) / êµ¬ì¡°??ë¡œê¹…(?Œì»¤ ?¬ë³¸). |
| `services/worker/{Dockerfile,requirements.txt}` | ?Œì»¤ ?´ë?ì§€(ë¹„ë£¨??Â·?˜ì¡´?? |
| `services/engine-analysis/app/main.py` | **ë¶„ì„ ?”ì§„** ???ì‡„ë§Â·ìê²©ì¦ëª??†ìŒ. ?´ë?ì§€?’ROI?’ì‹¤ì¸?ì§€??ì¢…í•©?ìˆ˜(ê³„ì•½ ?¤í‚¤ë§?ê²€ì¦?. |
| `services/engine-analysis/app/{roi.py,metrics.py,model.py}` | ROI ?¬ë¡­ / 10ì§€??ì¸¡ì • / baselineÂ·ML ë¡œë” seam. |
| `services/engine-analysis/{Dockerfile,requirements.txt}` | ë¶„ì„ ?”ì§„ ?´ë?ì§€(ë¹„ë£¨??Â·?˜ì¡´??OpenCV ??. |
| `services/engine-prescription/app/main.py` | **ì²˜ë°© ?”ì§„** ???…ë¦½ ì§„ì…??ë¶„ì„Â·?¤ë¬¸Â·PCR ì¤???). ?ìˆ˜?’ë“±ê¸‰â†’ë¹„ìœ¨ + ì§€?œë³„ ë¯¹ìŠ¤ ? íƒ. |
| `services/engine-prescription/app/rules.py` | ?•ì • ê·œì¹™(?±ê¸‰Â·ë¹„ìœ¨)Â·ë¯¹ìŠ¤ ? íƒ ë¡œì§(config ì£¼ì…). |
| `services/engine-prescription/app/survey.py` | **?¤ë¬¸ ?´ì„**(baseline): ?¤ë¬¸?’CVë¡??´ë ¤??ì§€??ë¯¼ê°?±Â·ë³µ?©ì„±) ?°ì¶œ. |
| `services/engine-prescription/app/config/mixes.example.json` | ë¯¹ìŠ¤ ? íƒ ê·œì¹™ ?ˆì‹œ config(?´ì˜?€ ì£¼ì… êµì²´). |
| `services/engine-prescription/{Dockerfile,requirements.txt}` | ì²˜ë°© ?”ì§„ ?´ë?ì§€(ë¹„ë£¨??Â·?˜ì¡´?? |

## `apps/` ???„ë¡ ???œë©´

| ?Œì¼ | ?¤ëª… |
|---|---|
| `apps/webapp-next/` | **SkinLens PWA**(Next.js App Router + PWA). Vercel ë°°í¬ ?€?? Supabase ë¡œê·¸????AI Server `/api` ?¸ì¶œ ??ë¹„ë™ê¸?Job ?´ë¦¬. |
| `apps/webapp/` | **?ˆê±°??Vite SPA**(React+TS). ?´ì „ ?„ë£Œ ???œê±° ?ˆì •. |
| `apps/homepage/public/index.html` | ê³µê°œ ?ˆí˜?´ì? ?ë¦¬?œì‹œ???´ì˜: Vercel ?´ê? ?ëŠ” ?œê±°). |
| `apps/devpage/public/index.html` | ê°œë°œ?í˜?´ì? ?ë¦¬?œì‹œ???ê¸° ?ˆì •). |

## `packages/` ??ê³µìš© ì½”ë“œ

| ?Œì¼ | ?¤ëª… |
|---|---|
| `packages/common/skinlens_contract/__init__.py` | **?”ì§„ ê³µìš© ê³„ì•½(source of truth)** ???¨ê³„ëª…Â?0ì§€?œÂ·ë“±ê¸‰í‘œÂ·`Survey`/`UPLOAD_FIELDS`Â·?”ì²­/?‘ë‹µ ?¤í‚¤ë§ˆÂ?ENGINE_CONTRACT_VERSION`. |
| `packages/common/README.md` | ê³µìš© ?¨í‚¤ì§€ ?¬ìš©ë²•Â·ê³„??ë²„ì „ ê·œì¹™. |

## `deploy/` ??AI Server ë°°í¬ ?¤íƒ(?¸í”„??

??ë²Œì˜ `compose.base.yml` ?„ì— ?˜ê²½ ?¤ë²„?ˆì´ë§?ê°ˆì•„?¼ì›?ˆë‹¤. **DB/Storage/Auth?????˜ê²½ Supabase**.

| ?Œì¼ | ?¤ëª… |
|---|---|
| `deploy/compose/compose.base.yml` | **?¤íƒ ?•ì˜.** ?¤íŠ¸?Œí¬ 2ë¶„í• Â·?”ì§„ ?ì‡„ë§Â·v3 ?˜ë“œ??ë¹„ë£¨?¸Â?no-new-privileges`Â·`cap_drop`Â·ë¦¬ì†Œ???í•œ). ?œë¹„?? gatewayÂ·workerÂ·engine-analysisÂ·engine-prescription. |
| `deploy/compose/compose.dev.yml` | dev ?¤ë²„?ˆì´(?ŒìŠ¤ `build:`Â·Supabase ?¬ìš©). |
| `deploy/compose/compose.staging.yml` | staging ?¤ë²„?ˆì´(`.env.images` ?œê·¸Â·Supabase ?¬ìš©). |
| `deploy/compose/compose.prod.yml` | prod ?¤ë²„?ˆì´(?œê·¸ ?¤í–‰Â·Supabase ?¬ìš©). |
| `deploy/compose/compose.gpu.yml` | ?”ì§„ GPU ë°°ì„  + ?™ì‹œ??ì§ë ¬???¤ë²„?ˆì´. |
| `deploy/compose/compose.tls.yml` | Caddy ?ë™ TLSÂ·HSTS ?¤ë²„?ˆì´. |
| `deploy/caddy/Caddyfile` | **AI Server TLS ?„ìš©.** `api.example.com`ë§?`reverse_proxy gateway:8000`. |
| `deploy/caddy/Caddyfile.staging` | ?¤í…Œ?´ì§• TLS ?¤ë²„?ˆì´??Caddyfile. |
| `deploy/scripts/sl` / `sl.ps1` | **?µí•© ê¸°ë™ CLI(ì§„ì‹¤?ë³¸).** ?˜ê²½ ë¬´ê? ê°™ì? ?™ì‚¬: `up/down/logs/ps/doctor/init/deploy`. compose ì¡°í•©Â·env-file ì¡°í•©???´ë??ì„œ ê²°ì •, env ?ëµ ???¤í–‰ ì¤?ì»¨í…Œ?´ë„ˆë¡?ì¶”ë¡ . Windows??PowerShell ???¬í•¨. |
| `deploy/scripts/deploy.sh` | **?œë²„ì¸?ê³µí†µ ë°°í¬.** ?œê·¸ ?ì êµì²´??GHCR pull)?’up??*?¬ìŠ¤ì²´í¬ ê²Œì´???ë™ ë¡¤ë°±**(flock ì§ë ¬??. `sl deploy`ê°€ ê°ì‹¼?? |
| `deploy/scripts/verify_server.sh` / `verify_client.ps1` / `verify_ops.sh` | ?œë²„ ?ê? ê²€ì¦?ëª¨ë“ˆ?•Â·hardening) / ?ê²© ?°ê²° ê²€ì¦?/ ?´ì˜ ?•ê¸°Â·?¬ë??????ê?. |
| `deploy/scripts/remote.ps1` / `remote.cmd` | **Windows ??Linux ?ê²© ëª¨ë‹ˆ?°ë§Â·?œì–´ CLI.** SSH ê²½ìœ ë¡?`status`(?¤ëƒ…?·Â·watch)Â·`ps`Â·`logs`Â·`health`Â·`doctor`(?½ê¸°) ?€ `up/down/restart/deploy`(?°ê¸°, prod ?•ì¸) + `tunnel`(ê´€ë¦¬í¬???¬ì›Œ??. ?‘ì† ?€?ì? `deploy/env/remote.env`. |
| `deploy/ops/remote-status.sh` | **?œë²„ì¸??íƒœ ?¤ëƒ…???ì´?„íŠ¸.** ?¨ì¼ SSH ?•ë³µ?¼ë¡œ ì»¨í…Œ?´ë„ˆÂ·?¬ìŠ¤Â·?”ìŠ¤??·ë©”ëª¨ë¦¬Â·?Â·GPUÂ·ìµœê·¼?¤ë¥˜ ?˜ì§‘(?½ê¸° ?„ìš©, `--json` ì§€??. `remote.ps1 status` ê°€ ?¸ì¶œ. |
| `deploy/env/remote.env.example` | ?ê²© ?´ì˜ ?‘ì† ?¤ì • ?œí”Œë¦?`RemoteTarget`Â·`RemoteDir`Â·`SshPort`Â·`IdentityFile`). ?¤ì œ `remote.env` ??gitignore. |
| `deploy/scripts/pg_backup.sh` / `wsl-backup-task.ps1` | DB ë°±ì—…(.env ê¸°ë°˜Â·?¤í”„?¬ì´?¸Â·ì•”?¸í™”Â·ë³´ì¡´ ?˜í•œÂ·?°ë“œë§? / WSL ê¹¨ìš°??Windows ?¤ì?ì¤„ëŸ¬ ?¸ë¦¬ê±? |
| `deploy/scripts/migrate_export.sh` / `migrate_import.sh` | ?´ê? ë²ˆë“¤ ?ì„±(??`.env` ?¬í•¨, ?”í˜¸???„ì†¡) / ?€???œë²„ ë³µì›Â·ê¸°ë™. |
| `deploy/supabase/policies/0001_rls_and_storage.sql` | RLS + Storage ?•ì±…(êµì°¨ ?¬ìš©???‘ê·¼ ì°¨ë‹¨). |
| `deploy/db/migrations/0001_init.sql` | ?´ì˜ ?¤í‚¤ë§?ë§ˆì´ê·¸ë ˆ?´ì…˜(?´ì˜?€ auto-DDL ?€?????Œì¼). |
| `deploy/db/README.md` | ë§ˆì´ê·¸ë ˆ?´ì…˜ ?ìš©/ë¡¤ë°± ?ˆë‚´. |
| `deploy/ops-jobs/retention.py` | ?„ë£Œ ?ë³¸ ?? œ + ë¯¸ì™„ë£??•ë¦¬(Supabase ë³´ì¡´ ??. |
| `deploy/ops-jobs/log-scrub.py` / `nginx-log-privacy.conf` | ??ë¡œê·¸ ? í°/URL/PII ë§ˆìŠ¤??/ ?‘ê·¼ ë¡œê·¸ ì¿¼ë¦¬?¤íŠ¸ë§Â·ì¸ì¦??œì™¸. |
| `deploy/ops-jobs/observability/{logging_config.py,alert.sh,crontab{,.example}}` | êµ¬ì¡°??JSON ë¡œê¹… / ?„ê³„ webhook ?Œë¦¼ / cron ?¤ì?ì¤? |
| `deploy/ops-jobs/restore-rehearsal.{sh,md}` | ë°±ì—… ë³µêµ¬+RPO/RTO ì¸¡ì •(?¤í…Œ?´ì§•) / ë³µêµ¬ ë¦¬í—ˆ???ˆì°¨Â·ê¸°ë¡?? |
| `deploy/ops-jobs/README.md` | ops-jobs(followup-P1) ë°°ì¹˜ êµ¬ì„±Â·ë°°ì„  ?”ë ¹. |
| `deploy/nginx/` | ? ï¸ **?ˆê±°??* ??3-Tier ?´ì „?¼ë¡œ ?œê±° ?ˆì •. ì±…ì„?€ Caddy/gatewayë¡??´ì£¼ ì¤? |

## `.github/workflows/` ??CI/CD

| ?Œì¼ | ?¤ëª… |
|---|---|
| `.github/workflows/deploy-static.yml` | ? ï¸ **?œê±° ?ˆì •** ??homepage/devpage ?•ì  ë°°í¬(?¹ì? Vercelë¡??´ê?). |
| `.github/workflows/deploy-built-service.yml` | gateway/worker ??**?œë²„?ì„œ ?´ë?ì§€ ë¹Œë“œ**(sha)??deploy.sh`(?¬ìŠ¤ ê²Œì´??ë¡¤ë°±). |
| `.github/workflows/deploy-webapp.yml` | ? ï¸ **?œê±° ?ˆì •** ??webapp ë¹Œë“œ/ë°°í¬(?¹ì? Vercelë¡??´ê?). |
| `.github/workflows/build-and-deploy-engine.yml` | engine-* ??**CI ë¹Œë“œ?’GHCR push**?’ì„œë²?pull??deploy.sh`. |
| `.github/workflows/tests.yml` | PR/?¸ì‹œ ??pytest ?¤í–‰. |

> ?´ì˜ ??ê°??Œí¬?Œë¡œ??`on.push.paths` ?„í„°(?? `services/gateway/**`)ë¥?ê±¸ì–´ ë³€ê²??œë¹„?¤ë§Œ ë¹Œë“œ?©ë‹ˆ??

## `tests/` ???µí•©Â·?¤ëª¨??pytest)

| ?Œì¼ | ?¤ëª… |
|---|---|
| `tests/test_environment.py` | ë¡œì»¬/?œë²„ ê³µí†µ ?µí•© ê²€ì¦?`TARGET_HOST`/`MODE=prod` ??. |
| `tests/common/test_contract.py` | ê³µìš© ê³„ì•½ ?¤í‚¤ë§?ë¶ˆë???ê²€ì¦? |
| `tests/gateway/test_{validation,health,storage,logging}.py` | ?…ë¡œ??ê²€ì¦Â·í—¬?¤Â·ìŠ¤? ë¦¬ì§€Â·ë¡œê¹… ?ŒìŠ¤?? |
| `tests/engine_analysis/test_{roi,metrics,score_endpoint}.py` | ROIÂ·ì§€?œÂ?/score` ?”ë“œ?¬ì¸???ŒìŠ¤?? |
| `tests/engine_prescription/test_{rules,survey,prescribe_endpoint}.py` | ê·œì¹™Â·?¤ë¬¸ ?´ì„Â·`/prescribe` ?ŒìŠ¤?? |
| `tests/worker/test_retry.py` | ?Œì»¤ ?¬ì‹œ??ë°±ì˜¤???ŒìŠ¤?? |
| `tests/integration/test_{pipeline,ownership}.py` | ?”ë“œ?¬ì—”???Œì´?„ë¼??/ ?Œìœ ê¶?êµì°¨ ?‘ê·¼ ì°¨ë‹¨) ?µí•©. |
| `tests/{conftest.py,_util.py,fixtures/README.md}` | ê³µí†µ ?½ìŠ¤ì²˜Â·ìœ ?¸Â·í”½?¤ì²˜ ?ˆë‚´(?¤ëª¨?¬ìš© ?˜í”Œ ?´ë?ì§€ ?ë¦¬). |

## `site/` ??ë¬¸ì„œ ?¬í„¸

| ?Œì¼ | ?¤ëª… |
|---|---|
| `site/index.html` | ë¬¸ì„œ?¸íŠ¸ ê°œìš” ???¬í„¸: êµ¬ì„±Â·**?°í????„í‚¤?ì²˜(?¬ì§„+?¤ë¬¸ ?ë¦„)**Â·ê°ì‚¬(P0/P1/P2). ë§í¬???„ì¬ monorepo ê²½ë¡œ. |
