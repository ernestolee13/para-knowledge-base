# USAGE — 실전 활용 가이드

설치 후 바로 참고할 수 있는 실전 패턴 모음. README는 개념·설치를 다루고, 이 문서는 **"매일 어떻게 굴리느냐"**를 다룬다.

> 이 가이드는 macOS + zsh + Obsidian 1.12+ + obsidian-cli 활성 + Claude Code 환경 기준. 다른 환경은 명령만 치환하면 동일하게 적용 가능.

---

## 1. 첫 설치 후 5분 셋업

```bash
# 1) 플러그인 설치 (이미 했다면 skip)
/plugin marketplace add ernestolee13/para-knowledge-base
/plugin install para-knowledge-base@para-knowledge-base

# 2) Obsidian vault 디렉토리에서 Claude Code 시작
cd ~/path/to/your-vault
claude

# 3) KB 초기화 (CLAUDE.md, _index.md, log.md 자동 생성)
/kb-init

# 4) 검증
/kb-lint    # broken/orphan/index drift 카운트만 확인
ls Inbox    # 비어있어야 정상
```

이 4단계로 vault에 KB 인프라가 깔린다. 이후엔 자동화·일상 루틴에 통합하는 게 본질.

---

## 2. 자동화 연계 — 매일/매주 자동 실행

이 플러그인의 가치는 **수동 호출이 아닌, 백그라운드 자동화에서 발현**된다. 권장 패턴 두 가지:

### 2-1. 모닝 루틴 → Inbox 자동 ingest

매일 아침 데일리 페이지를 만드는 스크립트가 있다면(`morning-routine.sh` 등), Inbox 카운트가 0보다 클 때 `/kb-ingest`를 자동 호출하도록 추가:

```bash
# morning-routine.sh 일부 예시
INBOX_COUNT=$(find "$VAULT/Inbox" -type f -name "*.md" 2>/dev/null | wc -l | tr -d ' ')

if [ "$INBOX_COUNT" -gt 0 ]; then
  INBOX_NAMES=$(ls "$VAULT/Inbox/" | head -5 | tr '\n' ', ')
  echo "[$(date)] Inbox has $INBOX_COUNT files — sending kb-ingest to tmux session..."

  tmux send-keys -t "daily-session" \
    "Inbox에 미처리 문서가 ${INBOX_COUNT}건 있어 (${INBOX_NAMES}). kb-ingest 스킬에 따라 각 문서를 분류하고 처리해줘. 처리 결과를 간단히 요약해줘." \
    Enter

  # 완료 polling (60초 timeout)
  KB_TIMEOUT=60
  KB_ELAPSED=0
  while [ "$KB_ELAPSED" -lt "$KB_TIMEOUT" ]; do
    if find "$VAULT/Inbox" -type f -name "*.md" | grep -q .; then
      sleep 5; KB_ELAPSED=$((KB_ELAPSED + 5))
    else
      echo "[$(date)] kb-ingest completed (${KB_ELAPSED}s)"; break
    fi
  done
else
  echo "[$(date)] Inbox empty — skipping kb-ingest"
fi
```

핵심:
- tmux 데일리 세션이 항상 떠 있어야 함 (launchd/systemd로 자동 시작)
- Inbox 0건이면 invoke 안 함 (불필요한 토큰 소모 방지)
- 완료 polling으로 다음 단계가 ingest 종료 후 진행됨

### 2-2. 위클리 리뷰 → /kb-lint 권고 첨부

주간 리뷰 스크립트(`weekly-review.sh` 등)에서 KB 건강 상태가 "정리 필요"이면 회고에 권고를 자동 첨부:

```bash
# weekly-review.sh 일부 예시
ORPHANS=$(obsidian orphans 2>/dev/null | wc -l | tr -d ' ')
UNRESOLVED=$(obsidian unresolved 2>/dev/null | wc -l | tr -d ' ')

if [ "$ORPHANS" -gt 50 ] || [ "$UNRESOLVED" -gt 100 ]; then
  cat >> "$WEEKLY_FILE" << EOF

## KB 정리 필요 (자동 감지)
- orphan files: $ORPHANS
- unresolved wikilinks: $UNRESOLVED
- 권고: 다음 주 시작 전 \`/kb-lint --fix\` 또는 \`/kb-index\` 실행
EOF
fi
```

핵심:
- 자동 실행이 아닌 *권고만* (lint --fix는 사용자 컨펌 후 수동 실행)
- 임계값(50/100)은 vault 크기에 맞게 조정

### 2-3. cron / launchd로 정기 호출 (옵션)

위 두 패턴이 너무 무거우면 cron으로 minimal:
```cron
# 매주 일요일 23:00 — lint 실행 후 결과만 캡처 (자동 fix 없음)
0 23 * * 0 obsidian unresolved > ~/.kb-lint-weekly-$(date +\%Y\%m\%d).log
```

---

## 3. Inbox 입력 채널 만들기

**가장 자주 빠뜨리는 단계**. 자동 ingest가 작동하려면 Inbox에 새 문서가 *흘러 들어와야* 한다. Inbox가 항상 0이면 ingest 자동화는 그림의 떡.

권장 입력 채널:

| 채널 | 도구 | 흐름 |
|---|---|---|
| **수동 드롭** | Finder / 파일 매니저 | 일상 메모를 .md로 저장 → Inbox에 drag |
| **클리퍼** | Obsidian Web Clipper / Defuddle | 웹 페이지 → 클린 마크다운 → Inbox |
| **Discord/Slack 봇** | n8n + 채널 webhook | 메시지 → 봇이 .md 저장 → Inbox |
| **RSS / 뉴스레터** | n8n + RSS feed | 새 글 → 요약 .md → Inbox |
| **음성 메모** | Voiset / Whisper.app | 받아쓰기 → .md → Inbox |
| **이메일** | Hazel / forward rule | 특정 라벨 메일 → .md → Inbox |

**최소 1개**는 만드는 걸 권장. 없으면 ingest는 무용.

---

## 4. 프로젝트 이동·생성·아카이빙 자동화

vault 내 변경 시 인덱스 깨지지 않게 하는 6단계 체크리스트(아래) 중 1·5번을 `obsidian move`로 자동화:

```bash
# 옛 방식 (수동 mv → wikilink 깨짐 → grep + replace 수동)
mv "1. Projects/old-name" "4. Archive/진행 중단 프로젝트/old-name"
grep -rln "\[\[old-name\]\]" . --include="*.md"   # 잔존 참조 찾아 수동 교체

# 새 방식 (obsidian move — Obsidian이 모든 wikilink 자동 갱신)
obsidian move path="1. Projects/old-name/file.md" to="4. Archive/진행 중단 프로젝트/old-name/file.md"
# 폴더 단위는 cli 미지원 — 그건 mv + 잔존 wikilink 검증 필수
```

전체 6단계 (vault `CLAUDE.md`에 박아두면 좋음):
1. **물리 이동/생성** — `obsidian move` 우선, 폴더 단위는 `mv`
2. **카테고리 인덱스 갱신** — `1. Projects/_index.md`, `4. Archive/_index.md` 등
3. **최상위 인덱스 갱신** — `0. Common/index.md` 카운트 변경 시
4. **Dashboard 핵심 목록 검토** — `0. Common/Dashboard.md` 영향 시 교체
5. **잔존 wikilink 검증** — `obsidian unresolved` 또는 `grep '\[\[<옛 이름>\]\]'`
6. **log.md append** — `0. Common/log.md` 맨 위에 한 줄: `[YYYY-MM-DD] <type> | 변경 요약 | 갱신한 인덱스 N개`

---

## 5. /kb-query 실전 예시 (Route별)

```bash
# Route A — 직접 폴더 접근
/kb-query "product launch 일정과 남은 리스크는?"
# → 1. Projects/product launch/ 직접 read

# Route B — 태그 횡단 (cli: obsidian tag name=<tag>)
/kb-query "research dashboard 관련 문서 전부"
# → obsidian tag name="#proj/research-dashboard" → 파일 리스트 받아 종합

# Route C — 백링크 (cli: obsidian backlinks file=<파일이름>)
/kb-query "Pricing Plan 문서를 참조하는 문서"
# → obsidian backlinks file="Pricing Plan"

# Route D — 인덱스/로그
/kb-query "최근 2주 활동 요약"
# → 0. Common/log.md 마지막 20줄

# Route E — 전문 검색 (cli: obsidian search:context query=<text>)
/kb-query "retry policy 설정"
# → obsidian search:context query="retry policy"
```

스킬 자체가 Route 자동 선택. 사용자는 **자연어로 묻기**만 하면 됨.

---

## 5-1. 쿼리 텔레메트리 — 나중에 검색 비용 분석하기

`/kb-query`가 잘 작동하는지 장기적으로 보려면, 답변 내용보다 **요청 단위의 운영 메타데이터**가 중요하다. 예를 들면 한 질문에 몇 개 문서를 읽었는지, 어떤 route를 탔는지, 도구 호출이 몇 번이었는지, 시간이 얼마나 걸렸는지, 토큰 사용량이 늘어나는지 같은 값이다.

권장 위치:

```text
0. Common/.telemetry/query-telemetry.jsonl
```

원칙:
- 지식 문서가 아니므로 `_index.md`에 등록하지 않는다.
- 일반 검색 중에는 읽지 않는다. 비용/성능/사용 패턴 분석을 할 때만 기간을 좁혀 읽는다.
- 번들된 공통 hook/emitter가 시간, 도구 호출, 경로, 가능한 token usage 같은 숫자를 기록한다.
- LLM은 숫자를 억지로 추정하지 말고, route·entrypoint·실제로 읽은 문서 같은 의미 정보만 `QuerySummary`로 보조한다.
- 한 의미 단위 query/build는 정확히 하나의 `operation_id`로 시작·step·summary·complete event를 묶고, 상위 agent request는 `request_id`로 별도 연결한다. 기존 `query_id`는 호환용 alias다.
- 단위 비용은 `QueryStart → QueryComplete` 또는 `BuildStart → BuildComplete`에서 재고, 세션/턴 전체 Stop 시간은 별도 진단값으로만 둔다.
- vault root를 제외한 PARA prefix·index 이름·spine path·telemetry/archive 위치는 `.para-kb/config.json`의 vault-relative 설정으로 취급한다. PARA Second Brain Viz도 이 파일을 자동 감지할 수 있으며, 이 플러그인 없이 독립 프로필로도 사용할 수 있다.
- prompt, 질문/답변, 노트 본문, 발췌, 절대경로는 기록하지 않는다. 분리할 수 없는 토큰은 추정하지 않고 N/A로 남긴다.

나중에 분석할 수 있는 질문:
- 검색 한 번에 평균 몇 개 문서를 읽는가?
- 직접 폴더 접근보다 full-text search 비중이 지나치게 높은가?
- 최근 들어 query당 소요 시간이나 토큰이 증가하는가?
- 특정 프로젝트만 검색 깊이가 깊어져 project hub나 더 나은 tag/index가 필요한가?
- vault 규모가 커져 단일 인덱스보다 project hub, graph view, external search/indexer가 필요한 시점인가?

---

## 6. 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `/kb-*` 스킬이 아예 안 보이거나 일부만 보임 (plugin은 설치된 것으로 표시됨) | 마켓플레이스 등록이 조용히 유실됨 — cache/install 기록은 남아있어도 등록이 빠지면 스킬이 죽는다 | `~/.claude/plugins/known_marketplaces.json`에 `para-knowledge-base` 항목이 있는지 확인. 없으면 `/plugin marketplace add ernestolee13/para-knowledge-base` 재등록 후 `/plugin install para-knowledge-base@para-knowledge-base`, `/reload-plugins` |
| `/kb-ingest` 호출해도 아무 변화 없음 | Inbox 0건 | Section 3 입력 채널 확인 |
| `/kb-lint`에서 broken 카운트가 너무 큼 | false positive 다수 (Templater, 코드 블록) | v0.2.0+ 룰 적용 후 진짜 broken만 수동 정리. 100개 이하면 정상 |
| `obsidian` 명령이 zsh: command not found | CLI 비활성 또는 PATH 문제 | Obsidian 1.12+ 인스톨러 + Settings → CLI Enable + 터미널 재시작 |
| `obsidian backlinks file="project-folder"` Error: File not found | 폴더 이름은 안 됨 | 정확한 파일 이름으로 입력 (`backlinks file="Project Overview"`) |
| 모닝 루틴이 ingest 트리거 안 함 | tmux 세션 부재 / Inbox 0 / 폴링 timeout | Section 2-1 스크립트와 에이전트 런타임 로그 확인 |
| plugin 캐시가 옛 버전이라 SKILL 변경 미반영 | 서드파티 마켓플레이스는 기본적으로 auto-update 비활성 | `/plugin marketplace update para-knowledge-base`로 카탈로그 갱신 후 `/reload-plugins` |
| 스킬 변경이 반영 안 되고 위 방법도 안 먹힘 | 로컬 plugin 캐시 손상 | `rm -rf ~/.claude/plugins/cache` 후 Claude Code 재시작, 플러그인 재설치 |
| `kb-query` 답이 빈 인용으로만 옴 | vault에 매칭 문서 없음 | Route 다시 시도(다른 키워드) 또는 vault에 그 정보 없는 게 사실 |
| log.md가 자동 갱신 안 됨 | `/kb-ingest`만 자동 append, 수동 변경은 별도 | 위 Section 4의 6단계 중 6번 직접 실행 (CLAUDE.md에 박아두는 것 권장) |

---

## 7. CLAUDE.md 권장 추가 내용

vault의 `CLAUDE.md`에 다음 내용을 추가하면 Claude가 자동으로 이 가이드를 따른다:

```markdown
## Plugin: para-knowledge-base

설치 후 5개 스킬 활성:
- `/kb-init` `/kb-ingest` `/kb-query` `/kb-lint` `/kb-index`

자동 연계:
- 모닝 루틴: Inbox >0 시 kb-ingest 자동 호출
- 위클리 리뷰: 건강 상태 정리 필요 시 권고 자동 첨부

## 변경 절차 (인덱스 깨지지 않게)

문서 추가·이동·아카이빙·삭제 시 6단계 체크리스트 (위 Section 4 참조)
```

이 두 섹션만 vault `CLAUDE.md`에 박아두면 Claude가 맥락을 자동 파악하고 절차를 따른다.

---

## 8. 자주 쓰는 명령 모음

```bash
# 정기 점검
/kb-lint                                # 건강 검사 (read-only)
/kb-lint --fix                          # 자동 픽스 가능한 항목 처리
/kb-index                               # 인덱스 전체 재구축 (큰 변경 후)

# Vault CLI 직접 호출 (스킬 없이)
obsidian unresolved                     # broken wikilink 리스트
obsidian orphans                        # 어디서도 참조 안 되는 파일
obsidian backlinks file="<파일이름>"     # 특정 파일을 참조하는 문서들
obsidian tag name=<태그>                # 태그로 파일 검색
obsidian search query="<텍스트>"        # 전문 검색
obsidian search:context query="<텍스트>" # 컨텍스트 라인 포함
obsidian move path="<from>" to="<to>"   # 파일 이동 + 자동 wikilink 갱신
obsidian property:read name=<key> file="<파일이름>"
obsidian property:set name=<key> value=<v> file="<파일이름>"

# 폴백 (CLI 없을 때)
grep -rln "\[\[<wikilink>\]\]" . --include="*.md"
find . -size -500c -mtime +30           # 빈 + 오래된 파일
```

---

## 9. 권장 운영 리듬

| 빈도 | 작업 |
|---|---|
| 매일 (자동) | 모닝 루틴이 Inbox 체크 + 비어있지 않으면 kb-ingest |
| 매주 (반자동) | 위클리 리뷰가 건강 상태 체크 + 정리 필요 시 권고 |
| 분기 (수동) | `/kb-lint --fix` 풀 호출, 빈 데일리/위클리 cleanup, broken wikilink 진짜 100개 정리 |
| 큰 변경 후 (수동) | `/kb-index` (폴더 대량 재배치 등) |

---

## 10. 개인화 체크리스트

Plugin은 vault 본인 설정을 따른다 — 처음 셋업 후 다음을 본인 환경에 맞게 한 번 점검:

- **`.obsidian/app.json` `userIgnoreFilters`** — 개인 일기·템플릿·드래프트처럼 검색 제외할 폴더. Obsidian Settings → Files & Links → Excluded files. plugin이 lint 결과 자동 후처리.
- **`CLAUDE.md` frontmatter `type` enum** — 본인 vault에서 실제 쓰는 type 값으로 갱신. `grep -rh '^type: ' . --include='*.md' | sort -u`로 실사용 확인 후 표준 업데이트.
- **태그 prefix** — `#proj/<name>`, `#topic/<topic>`, `#study/paper/<topic>` 중 본인 도메인에 맞는 체계 결정 후 일관 사용. CLAUDE.md에 명시.
- **`_index.md` 카테고리** — PARA 4개 대분류 _index에 sub-section 분류. 분류 기준은 vault 콘텐츠 따라 (논문이면 주제별, 책이면 장르별 등).
- **프로젝트 허브 사용 여부** — 프로젝트 폴더가 크거나 장기화되면 `1. Projects/<slug>/_index.md`를 local entrypoint로 둘 수 있다. 작고 단순한 vault라면 만들지 않아도 된다.
- **query/build telemetry 사용 여부** — 검색·구축 비용과 깊이를 분석하고 싶다면 `.para-kb/config.json`에서 활성화한다. 번들 hook/emitter가 기록하며 PARA Second Brain Viz가 같은 설정을 자동 감지할 수 있다. 시각화 플러그인 자체는 PARA Knowledge Base 없이도 독립 실행된다.
- **모닝 루틴 ingest 자동 호출** — Section 2-1 패턴을 본인 자동화 스크립트(`morning-routine.sh` 등)에 추가.
- **log.md 활용 습관** — 모든 vault 변경(이동·아카이빙·cleanup) 시 한 줄 append. KB가 살아있게 만드는 단일 source of truth.

---

## 11. 안티패턴 — 흔한 함정

### Sub-`_index.md`를 무작정 늘리기

❌ `2. Areas/Books/_index.md`, `3. Resources/Travel/_index.md` 등 모든 하위 폴더에 추가 _index 만들기.
✅ 기본은 PARA 대분류 `_index.md`에 sub-section으로 catalog. 단, 장기 프로젝트처럼 자체 문서가 많고 자주 조회되는 폴더는 `1. Projects/<slug>/_index.md`를 project hub로 둘 수 있다. 핵심은 "모든 폴더에 인덱스"가 아니라 "자주 진입하는 큰 단위에만 local entrypoint"다.

### `obsidian unresolved` 카운트를 그대로 진짜 broken으로 받기

❌ unresolved 282건을 모두 정리해야 한다고 받아들이기.
✅ 카테고리 분류 — Templater 변수, 외부 경로(`./`, `/`, `http`), 폴더 wikilink, 옛 데일리 prev-next 등은 false positive 또는 batch fix 가능. 진짜 broken은 보통 10-20% 수준.

### Target 카운트로 fix 진행도 측정

❌ `obsidian unresolved` 카운트만 보고 fix 효과 판단. 100건 fix해도 카운트 변동 적을 수 있음.
✅ Target 카운트 + instance 카운트(`grep -rln '[[<target>]]' . | wc -l`) 둘 다 추적. instance 줄어드는 게 진짜 fix 진행도.

### 모든 파일을 wikilink로 연결하려는 욕심

❌ orphan 0건 추구.
✅ 자연 orphan 인정 — 개인 일기, archive, 일회성 메모는 link 안 되는 게 정상. `userIgnoreFilters`로 자동 제외.

### 매번 `_index.md` 카운트 갱신 잊기

❌ 파일 추가/삭제 시 _index.md의 "활성 N개" 같은 카운트 그대로 두기.
✅ 변경 시 즉시 갱신 또는 큰 변경 후 `/kb-index`로 일괄 재생성.

---

## 더 알아보기

- [README.md](./README.md) — 개념, 설치, 5개 스킬 상세
- [CHANGELOG.md](./CHANGELOG.md) — 버전 변경 내역
- [Karpathy llm-wiki Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — 원본 패턴
- [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) — Obsidian CLI / markdown / bases 스킬 (이 플러그인과 보완)
