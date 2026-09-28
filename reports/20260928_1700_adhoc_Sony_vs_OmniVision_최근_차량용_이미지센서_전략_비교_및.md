# Sony vs OmniVision 최근 차량용 이미지센서 전략 비교 및 삼성 CIS 대응 방향

## 요약 (Executive Summary)

- **Sony는 “차량 카메라 시스템 아키텍처 선점” 전략**입니다. IMX828에서 8MP급 ADAS 센서에 **MIPI A-PHY를 센서 내부에 통합**해 외장 Serializer 제거, 저전력·소형화·EMI/노이즈 내성을 내세우고 있습니다. HDR, 기능안전, 사이버보안까지 포함한 프리미엄 ADAS 플랫폼형 접근입니다.
- **OmniVision은 “빠른 양산·포트폴리오 확장·Tier-1 설계 편의성” 전략**입니다. OX08D30은 이미 양산 중이며, TheiaCel/LOFIC 기반 HDR·LED Flicker Mitigation, 소형 a-CSP, 기존 OX08D10과 pin-to-pin 호환성을 강조합니다.
- **인캐빈(DMS/OMS)에서도 경쟁이 본격화**됐습니다. Sony IMX775는 5MP RGB-IR, 940nm QE 35%, 110dB RGB HDR을 제시했고, OmniVision OX05C는 5MP BSI Global Shutter HDR, Nyxel NIR, on-chip RGB-IR separation으로 단일 카메라 DMS/OMS를 겨냥합니다.
- **삼성 ISOCELL Auto 1H1은 8.3MP·120dB HDR·CornerPixel 기반 LFM 경쟁력이 있으나**, 공개 기준으로는 Sony의 인터페이스 통합, OmniVision의 LOFIC/양산 속도 및 인캐빈 라인업 대비 보완 필요성이 큽니다.
- **대응 방향은 ①8MP ADAS Gen2 조기 정의, ②A-PHY/보안 통합 옵션, ③5MP RGB-IR 인캐빈 제품군 신설, ④Mobileye·DMS 알고리즘·Tier-1 레퍼런스 플랫폼 확보**가 핵심입니다.

---

## 1. 시장 배경: 차량용 CIS는 “고성능 센서 + 시스템 통합” 경쟁으로 이동

Yole 분석을 인용한 Optics.org에 따르면 CMOS 이미지센서 시장은 2024년 **232억 달러** 규모였고 2030년 **300억 달러**를 상회할 것으로 전망됩니다. 성장 동력으로 모바일 회복과 함께 **자동차 ADAS, 인캐빈 모니터링, 서라운드뷰**가 명시됐습니다. 자동차 카메라 모듈은 2023년 **2.36억 개**, 차량당 평균 약 3개 수준으로 언급됐습니다. [8]

최근 경쟁 포인트는 단순 해상도 경쟁에서 다음 5가지로 확대되고 있습니다.

1. **8MP 이상 고해상도 ADAS**
2. **HDR + LED Flicker Mitigation + 저조도 성능**
3. **고온 안정성 및 기능안전/사이버보안**
4. **카메라 모듈 BOM·전력·열·크기 절감**
5. **DMS/OMS용 RGB-IR, NIR 감도, Global Shutter**

---

## 2. Sony 전략: 프리미엄 ADAS 아키텍처와 인터페이스 통합 선점

### 2.1 핵심 제품: IMX828 — “센서 내부 MIPI A-PHY”로 시스템 가치 제안

Sony는 2025년 10월 IMX828을 발표했습니다. 핵심은 **차량용 CMOS 이미지센서 최초로 MIPI A-PHY 인터페이스를 내장**했다는 점입니다. Sony는 이를 통해 기존 외장 Serializer IC가 필요 없고, 카메라 시스템 소형화, 저전력화, 열 설계 단순화, 외부 노이즈에 대한 전송 오류 내성 향상을 제공한다고 설명합니다. [1]

| 항목 | Sony IMX828 |
|---|---:|
| 용도 | ADAS/AD 외부 카메라 |
| 해상도 | 약 8.34MP, 3848×2168 |
| 광학 포맷 | 1/1.7형, 9.28mm diagonal |
| 픽셀 | 2.1µm |
| 프레임레이트 | 최대 45fps |
| HDR | 120dB with LFM / 150dB dynamic range priority |
| 고온 | 최대 junction temperature 125°C 조건 언급 |
| 인터페이스 | MIPI D-PHY + I2C 또는 MIPI A-PHY |
| 기능안전 | ISO 26262, HW metrics ASIL-B, 개발 프로세스 ASIL-D |
| 사이버보안 | ISO/SAE 21434 프로세스, 인증/위변조 검출 옵션 |
| 샘플 | 2025년 11월 예정 |

**전략적 의미**

- Sony는 단순 센서 스펙이 아니라 **카메라-ECU 연결 구조**를 장악하려 하고 있습니다.
- MIPI A-PHY 내장은 Tier-1 입장에서 Serializer BOM, 전력, 보드 면적, 열 설계 부담을 줄이는 메시지입니다.
- Mobileye와 개발한 **dual-HDR capture mode**도 명시되어 있어, 알고리즘/SoC 생태계와 연동한 설계승인 전략으로 해석됩니다. [1]

### 2.2 인캐빈 제품: IMX775 — 고해상도 RGB-IR + NIR 감도

Sony IMX775는 인캐빈 모니터링용 RGB-IR 센서입니다. 5MP급 해상도, 2.1µm 픽셀, 940nm NIR QE 35% 이상, RGB 110dB HDR, Hybrid rolling/global shutter 구조를 제시합니다. 양산 출하는 2026년 봄 예정입니다. [2]

| 항목 | Sony IMX775 |
|---|---:|
| 용도 | DMS/OMS 인캐빈 모니터링 |
| 해상도 | 약 5.04MP, 2593×1945 |
| 픽셀 | 2.1µm |
| 프레임레이트 | 60fps |
| NIR QE | 940nm에서 ≥35% |
| RGB DR | 110dB |
| 특징 | RGB-IR 단일칩, NIR 성분 제거 알고리즘, context switching |
| 안전/품질 | AEC-Q100 Grade 2 예정, ISO 26262 ASIL-B 대응 |

**전략적 의미**

- Sony는 외부 ADAS와 인캐빈을 모두 포괄하는 **고부가 차량용 CIS 라인업**을 구축 중입니다.
- IMX775는 실내 전체를 단일 카메라로 커버하려는 OEM/Tier-1 요구에 대응합니다.
- on-chip NIR 제거 및 업스케일링 기능은 외부 ISP 부담을 줄이는 방향입니다.

### 2.3 제조/기술 기반: TSMC JV로 차세대 센싱 대응

Sony와 TSMC는 2026년 5월 차세대 이미지센서 개발·제조를 위한 전략적 파트너십 MOU를 발표했습니다. Sony는 이 JV가 **automotive, robotics 등 physical AI 기회**를 겨냥한다고 명시했습니다. [3]

**해석**

- Sony의 차량용 CIS 전략은 제품 단품이 아니라 **공정·패키징·AI 센싱 플랫폼 경쟁력 강화**와 연결되어 있습니다.
- 장기적으로 고부가 적층 센서, 엣지 센싱, 고성능 픽셀 구조에서 Sony의 기술 리더십이 강화될 가능성이 있습니다.

---

## 3. OmniVision 전략: LOFIC 기반 빠른 제품 전개와 설계 호환성

### 3.1 핵심 제품: OX08D30 — 8MP ADAS 센서의 즉시 양산 카드

OmniVision OX08D30은 2026년 9월 AutoSens Europe에서 공개된 8MP 차량용 CMOS 이미지센서입니다. Electronics Weekly 및 EFY 보도와 OmniVision 제품 페이지 기준, TheiaCel 기술 기반 HDR, LFM, 2.1µm 픽셀, 1/1.729형, 3840×2160, 40fps, 92-pin a-CSP 패키지가 확인됩니다. 샘플 공급 중이며 이미 양산 중이라고 보도됐습니다. [4][5][6]

| 항목 | OmniVision OX08D30 |
|---|---:|
| 용도 | 전방 ADAS/AD 외부 카메라 |
| 해상도 | 8MP, 3840×2160 |
| 광학 포맷 | 1/1.729형 |
| 픽셀 | 2.1µm |
| 프레임레이트 | 40fps |
| 패키지 | 92-pin a-CSP |
| 기술 | TheiaCel, HDR, LFM, LOFIC |
| 셔터 | Rolling Shutter |
| 특징 | OX08D10 pin-to-pin 호환, 양산 중 보도 |

**전략적 의미**

- OmniVision은 Sony처럼 인터페이스 통합을 전면에 내세우기보다, **HDR/LFM/저조도/소형화/전력/호환성**을 통해 빠른 설계 채택을 유도합니다.
- OX08D10과 pin-to-pin 호환은 기존 Tier-1 설계를 업그레이드하기 쉬운 강력한 무기입니다.
- “이미 양산” 메시지는 2026~2027년 신차 프로그램에서 즉시 채택 가능한 공급 안정성 신호입니다.

### 3.2 OX08D20 — Mobileye 협업 및 60fps 듀얼유스

OmniVision은 2025년 10월 OX08D20도 발표했습니다. OX08D10의 업그레이드 제품으로, Mobileye와 협업한 capture scheme을 통해 근거리 물체 motion blur를 줄이고 저조도 성능을 개선한다고 설명합니다. 60fps, MIPI CSE 2.0 대응 사이버보안, 소형 a-CSP를 강조하며, 샘플은 2025년 11월, 양산은 2026년 4분기 예정입니다. [7]

| 항목 | OmniVision OX08D20 |
|---|---:|
| 용도 | ADAS/AD 외부 카메라 |
| 해상도 | 8MP, 3840×2160 |
| 프레임레이트 | HDR3 60fps, HDR4 55fps 등 |
| 기술 | TheiaCel, LFM |
| 파트너십 | Mobileye 협업 capture scheme |
| 보안 | MIPI CSE 2.0 |
| 양산 | 2026년 4분기 예정 |

### 3.3 인캐빈: OX05C — Global Shutter HDR + Nyxel NIR

OmniVision OX05C는 5MP BSI Global Shutter HDR 센서로, DMS/OMS를 겨냥합니다. 2.2µm 픽셀, Nyxel NIR, 940nm NIR 파장 성능, on-chip RGB-IR separation, 30% 작은 패키지, 단일 카메라 DMS/OMS 지원을 내세웁니다. 샘플은 공급 중이며 2026년 양산 예정입니다. [9]

| 항목 | OmniVision OX05C |
|---|---:|
| 용도 | DMS/OMS 인캐빈 |
| 해상도 | 5MP, 2592×1944 |
| 픽셀 | 2.2µm |
| 셔터 | Global Shutter |
| 기술 | BSI GS HDR, Nyxel NIR, RGB-IR |
| 프레임레이트 | 60fps, 3-exposure HDR |
| 패키지 | 6.61mm × 5.34mm, 기존 OX05B 대비 30% 축소 |
| 양산 | 2026년 예정 |

**전략적 의미**

- OmniVision은 DMS/OMS에서 **Global Shutter + HDR + NIR** 조합을 강조합니다.
- Smart Eye와 같은 알고리즘 생태계 코멘트를 전면에 내세워, 센서 단품이 아니라 **알고리즘 정확도 향상** 관점으로 OEM을 설득하고 있습니다. [9]
- 동일 렌즈 업그레이드 가능성 등 Tier-1 설계 비용 절감 메시지가 강합니다.

---

## 4. Sony vs OmniVision 전략 비교

| 구분 | Sony | OmniVision | 삼성 관점 시사점 |
|---|---|---|---|
| 핵심 전략 | 프리미엄 시스템 아키텍처 선점 | 빠른 양산, 포트폴리오 확장, 설계 호환성 | 삼성은 기술 스펙뿐 아니라 시스템 비용 절감 메시지 필요 |
| 외부 ADAS 제품 | IMX828 8.34MP, MIPI A-PHY 내장, 150dB HDR | OX08D30/OX08D20 8MP, TheiaCel/LOFIC, LFM, 소형 a-CSP | 8MP Gen2에서 HDR·LFM·전력·패키지·인터페이스 동시 대응 필요 |
| 차별화 포인트 | 외장 Serializer 제거, A-PHY, 기능안전/보안, Mobileye dual-HDR | pin-to-pin 호환, 양산 속도, Mobileye capture scheme, 저전력/소형화 | Tier-1 설계 전환 장벽을 낮추는 패키지/핀 호환 로드맵 필요 |
| 인캐빈 | IMX775 RGB-IR, 5MP, 940nm QE 35%, 110dB | OX05C 5MP BSI GS HDR, Nyxel, on-chip RGB-IR separation | 삼성 인캐빈 RGB-IR/GS 제품 라인업 공백 보완 필요 |
| 생태계 | MIPI A-PHY, Mobileye, TSMC JV | Mobileye, Smart Eye, AutoSens 중심 데모 | 알고리즘·SoC·Tier-1 공동 레퍼런스 확보가 중요 |
| 출시 타이밍 | IMX828 샘플 2025.11, IMX775 양산 2026 봄 | OX08D30 이미 양산 보도, OX08D20 Q4’26, OX05C 2026 | 단기 경쟁은 OmniVision, 중장기 구조 경쟁은 Sony가 더 위협적 |
| 가격 전략 | 공개 정보 부족 | 공개 정보 부족 | 가격 추정은 불가. 다만 OmniVision은 BOM·호환성으로 TCO 절감 강조 |

---

## 5. 삼성 현재 위치: ISOCELL Auto 1H1의 강점과 보완점

삼성 ISOCELL Auto 1H1은 공개 자료 기준 **8.3MP**, AD/ADAS용, CornerPixel 기반 **single exposure HDR**, LED Flicker Mitigation, motion artifact-free HDR, **최대 120dB HDR at 36fps**, ASIL-B, AEC-Q100 Grade 2+를 강조합니다. [10]

### 강점

- 8MP급 ADAS용 해상도 보유
- CornerPixel 기반 single exposure HDR 및 LFM 메시지 보유
- ASIL-B, AEC-Q100 Grade 2+ 등 자동차 품질 요건 대응
- 삼성의 반도체 포트폴리오: CIS, SoC, 메모리, 파운드리, 패키징까지 연계 가능

### 보완점

- Sony IMX828 대비 **인터페이스 통합(A-PHY 내장) 메시지 부재**
- OmniVision OX08D30 대비 **양산/디자인윈 확대 신호와 pin-to-pin 업그레이드 메시지 부족**
- Sony/OmniVision 대비 **인캐빈 RGB-IR/Global Shutter/NIR 제품군 가시성 부족**
- Tier-1·알고리즘 업체와의 **공동 레퍼런스 및 실차 데모 공개 부족**

---

## 삼성 CIS 사업 시사점 및 제언

### A. 단기: 8MP ADAS 경쟁 갭 클로징 및 고객 데모 강화

| Action item | 내용 | 담당 영역 | 시급도 |
|---|---|---|---|
| 1H1 경쟁 벤치마크 | IMX828, OX08D30, OX08D20 대비 HDR, LFM, 저조도, 고온 노이즈, 전력, 패키지 면적, EMI 평가 | 제품기획/화질/AE | 즉시 |
| Tier-1 데모킷 | 1H1 기반 전방 ADAS 레퍼런스 카메라, ISP 튜닝, LED 신호등/터널/야간 시나리오 데모 제작 | 시스템FAE/응용기술 | 즉시 |
| 고객 메시지 재정의 | “8.3MP + single exposure HDR + LFM + ASIL-B”를 BOM/TCO 관점으로 재패키징 | 마케팅/영업 | 1개월 |
| OX08D30 방어자료 | OmniVision의 pin-to-pin 호환, 양산, 20% 저전력/50% 소형화 주장에 대한 기술 비교자료 작성 | 전략/상품기획 | 1개월 |

### B. 중기: ISOCELL Auto 8MP Gen2 로드맵 조기 확정

**권고 스펙 방향**

- HDR: 현 120dB급에서 **140~150dB급 옵션** 검토
- 프레임레이트: 8MP 기준 **40fps 이상**, 가능하면 60fps 듀얼유스 옵션
- LFM: single exposure 기반 LFM 유지·강화
- 저조도: LOFIC 또는 대용량 캐패시턴스 구조 검토
- 고온: 125°C junction 조건에서 노이즈/HDR 성능 보증 메시지 필요
- 패키지: a-CSP 소형 패키지, bare die 옵션, 기존 1H1 upgrade path 제공
- 호환성: 고객 전환을 위해 **pin-compatible 또는 module-compatible variant** 검토

### C. 차세대 인터페이스 대응: A-PHY 내장 또는 레퍼런스 솔루션

Sony IMX828의 핵심 위협은 화소 스펙이 아니라 **외장 Serializer 제거**입니다. 삼성도 다음 중 하나를 선택해야 합니다.

1. **A-PHY 내장형 CIS variant 개발**
2. Valens/ADI/MIPI A-PHY PHY 업체와 공동 레퍼런스 모듈 개발
3. 1H1 및 Gen2용 “Serializer-less roadmap”을 고객에게 선제 제시

권고는 **2단계 접근**입니다.

- 2026년: 외부 PHY/Serializer 파트너와 레퍼런스 보드 제공
- 2027년 이후: A-PHY 또는 차세대 차량 인터페이스 내장형 CIS 검토

### D. 인캐빈 RGB-IR 제품군 신설

Sony IMX775와 OmniVision OX05C가 동시에 5MP급 인캐빈을 밀고 있어, 삼성도 DMS/OMS 대응 제품군을 별도 축으로 가져가야 합니다.

**권고 제품 방향**

| 항목 | 목표 방향 |
|---|---|
| 해상도 | 5MP RGB-IR, 3MP cost-down variant 병행 |
| NIR | 940nm QE 35% 이상 목표 |
| 셔터 | Global Shutter 또는 Hybrid GS/RS |
| HDR | RGB 110dB 이상 |
| 온칩 기능 | RGB-IR separation, NIR upscaling, ROI/context switching |
| 보안 | 센서 인증, 이미지 위변조 검출, 통신 인증 |
| 파트너 | Smart Eye, Seeing Machines, Tobii 등 DMS 알고리즘 업체와 공동 검증 추진 |

### E. 생태계 전략: 센서 단품에서 “카메라 시스템 플랫폼”으로 전환

Sony와 OmniVision 모두 Mobileye, Smart Eye, MIPI 생태계를 활용하고 있습니다. 삼성은 다음 3개 레퍼런스를 동시에 확보해야 합니다.

1. **ADAS 전방 8MP 레퍼런스**: Mobileye/NVIDIA/Qualcomm/국내 SoC와 호환성 검증
2. **인캐빈 DMS/OMS 레퍼런스**: 알고리즘 업체와 데이터셋·튜닝 공동 진행
3. **Tier-1 모듈 레퍼런스**: LG이노텍, HL만도, 현대모비스, Continental, Bosch, Valeo 등과 공동 PoC

---

## 모니터링 포인트

1. **Sony IMX828의 실제 양산 시점 및 디자인윈**
   - A-PHY 내장 구조가 주요 OEM/Tier-1에서 표준으로 확산되는지 확인 필요

2. **MIPI A-PHY 및 MIPI CSE 2.0 채택 속도**
   - 차세대 차량 카메라 인터페이스가 센서 구매 조건으로 들어가는지 추적

3. **OmniVision OX08D30 양산 고객**
   - OX08D10 고객군이 OX08D30으로 얼마나 빠르게 전환하는지 확인

4. **OX08D20 Q4’26 양산 지연 여부**
   - Mobileye 협업 capture scheme이 실제 고객 프로젝트에 들어가는지 추적

5. **인캐빈 DMS/OMS 규제 강화**
   - EU, 중국, 북미 DMS/OMS 의무화 흐름에 따라 5MP RGB-IR 수요가 확대될 가능성

6. **Sony-TSMC JV 본계약 및 투자 규모**
   - automotive/robotics용 next-gen sensor 공정 로드맵이 구체화되는지 확인

7. **중국 CIS 업체 확장**
   - OmniVision 외 SmartSens, GalaxyCore, Gpixel의 차량용 진입 확대 여부

---

## 출처

1. Sony Semiconductor Solutions, 2025-10-28, “Sony Semiconductor Solutions to Release Industry’s First CMOS Image Sensor for Automotive Applications with Built-in MIPI A-PHY Interface”, https://www.sony-semicon.com/en/news/2025/2025102801.html  
2. Sony Semiconductor Solutions, 2025-10-02, “Sony Semiconductor Solutions to Release RGB-IR Image Sensor for In-Cabin Monitoring Cameras…”, https://www.sony-semicon.com/en/news/2025/2025100201.html  
3. Sony Semiconductor Solutions, 2026-05-08, “Sony Semiconductor Solutions and TSMC Sign MOU to Establish Strategic Partnership for Next-Generation Image Sensors”, https://www.sony-semicon.com/en/news/2026/2026050801.html  
4. Electronics Weekly, 2026-09-22, “Omnivision’s OX08D30 8-megapixel CMOS automotive image sensor eyes ADAS”, https://www.electronicsweekly.com/news/business/omnivisions-ox08d30-8-megapixel-cmos-automotive-image-sensor-eyes-adas-2026-09/  
5. Electronics For You, 2026-09-24, “Automotive Image Sensor Improves HDR Vision For Driving”, https://www.electronicsforu.com/news/automotive-image-sensor-improves-hdr-vision-for-driving  
6. OMNIVISION, accessed 2026-09-28, “OX08D30 Product Page”, https://www.ovt.com/products/ox08d30/  
7. OMNIVISION, 2025-10-07, “OMNIVISION Introduces Next-Generation 8MP Image Sensor for Exterior Automotive Cameras”, https://www.ovt.com/press-releases/omnivision-introduces-next-generation-8mp-image-sensor-for-exterior-automotive-cameras/  
8. Optics.org, 2025-07-29, “CMOS imaging sensors market bounces back to growth”, https://www.optics.org/news/cmos-imaging-sensors-market-bounces-back-to-growth  
9. OMNIVISION, 2025-10-07, “OMNIVISION Announces Automotive Industry’s First Global Shutter HDR Sensor for In-Cabin Driver and Occupant Monitoring Systems”, https://www.ovt.com/press-releases/omnivision-announces-automotive-industrys-first-global-shutter-hdr-sensor-for-in-cabin-driver-and-occupant-monitoring-systems/  
10. Samsung Semiconductor, accessed 2026-09-28, “ISOCELL Auto 1H1”, https://semiconductor.samsung.com/image-sensor/automotive-image-sensor/isocell-auto-1h1/