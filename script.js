// All reference formulas/tables below are transcribed from the official
// 대입정보포털(adiga.kr) "전형 요강 및 결과" disclosure for 고려대학교[본교],
// 2026학년도 (unvCd=0000069, searchSyr=2026). Where the source page embedded
// a formula as an image that didn't convert cleanly to text (the 학생부교과
// interpolation step), that gap is filled with a documented, standard
// linear-interpolation reconstruction — flagged in the UI, not presented as
// an official figure.

const ENGLISH_DEDUCTION = { 1: 0, 2: 3, 3: 6, 4: 9, 5: 12, 6: 15, 7: 18, 8: 21, 9: 24 };
const HISTORY_DEDUCTION = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0.2, 6: 0.4, 7: 0.6, 8: 0.8, 9: 2.0 };
const GRADE_SCORE = { 1: 100, 2: 96, 3: 92, 4: 86, 5: 70, 6: 55, 7: 40, 8: 20, 9: 0 };

function $(id) { return document.getElementById(id); }

function switchTab(name) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll('.panel').forEach(p => p.classList.toggle('active', p.id === 'panel-' + name));
}

function stampReveal(box) {
  box.classList.remove('stamp-hit');
  // force reflow so the animation restarts on repeated clicks
  void box.offsetWidth;
  box.classList.add('stamp-hit');
}

function calcJeongsi() {
  const kor = clamp(Number($('korPercentile').value), 0, 100);
  const math = clamp(Number($('mathPercentile').value), 0, 100);
  const tamgu = clamp(Number($('tamguPercentile').value), 0, 100);
  const eng = Number($('engGrade').value);
  const hist = Number($('histGrade').value);

  const korScore = 200 * (kor / 100);
  const mathScore = 200 * (math / 100);
  const tamguScore = 160 * (tamgu / 100);
  const engDeduct = ENGLISH_DEDUCTION[eng] ?? 0;
  const histDeduct = HISTORY_DEDUCTION[hist] ?? 0;
  const total = korScore + mathScore + tamguScore - engDeduct - histDeduct;

  $('jeongsiScore').innerHTML = total.toFixed(2) + ' <span>/ 560점</span>';
  $('jeongsiBreakdown').innerHTML = `
    <div><span>국어 (백분위 반영, 배점 200)</span><span>${korScore.toFixed(1)}</span></div>
    <div><span>수학 (백분위 반영, 배점 200)</span><span>${mathScore.toFixed(1)}</span></div>
    <div><span>탐구 (백분위 반영, 배점 160)</span><span>${tamguScore.toFixed(1)}</span></div>
    <div><span>영어 ${eng}등급 감점</span><span>-${engDeduct.toFixed(1)}</span></div>
    <div><span>한국사 ${hist}등급 감점</span><span>-${histDeduct.toFixed(2)}</span></div>
  `;
  stampReveal($('jeongsiResult'));
}

function calcGyogwa() {
  const avgGrade = clamp(Number($('avgGrade').value), 1, 9);
  const n = Math.min(9, Math.floor(avgGrade));
  const frac = avgGrade - n;
  const scoreN = GRADE_SCORE[n];
  const scoreNext = GRADE_SCORE[Math.min(9, n + 1)];
  const gwamokScore = n === 9 ? scoreN : scoreN - frac * (scoreN - scoreNext);
  const reflected = gwamokScore * 0.9;
  const total = reflected + 10; // 서류 10점 고정 반영

  $('gyogwaScore').innerHTML = total.toFixed(2) + ' <span>/ 100점</span>';
  $('gyogwaBreakdown').innerHTML = `
    <div><span>교과평균등급점수</span><span>${gwamokScore.toFixed(2)}</span></div>
    <div><span>학생부(교과) 반영점수 (×0.9)</span><span>${reflected.toFixed(2)}</span></div>
    <div><span>서류 반영점수 (고정)</span><span>10.00</span></div>
  `;
  stampReveal($('gyogwaResult'));
}

function clamp(n, min, max) {
  if (Number.isNaN(n)) return min;
  return Math.min(max, Math.max(min, n));
}

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});
$('jeongsiCalcBtn').addEventListener('click', calcJeongsi);
$('gyogwaCalcBtn').addEventListener('click', calcGyogwa);
