/* Text/Ant-like UI without external deps */
const el = (id) => document.getElementById(id);

let env;
let logLines = [];
const LOG_LIMIT = 40;
const HISTORY_LIMIT = 50;
const historyStack = [];
let compactMode = false;
let currentColumns = 2;

// worker code (same logic, no graphics)
const workerCode = `
class Board {
  constructor() {
    this.score = 1;
    this.reward = 0;
    this.diceUse = 0;
    this.isDouble = false;
    this.cards = [];
    this.exScores = new Array(6).fill(0);
    this.exValues = { min: new Array(6).fill(0), max: new Array(6).fill(0), std: new Array(6).fill(0), mid: new Array(6).fill(0) };
    this.exScore = Infinity;
    this.exAction = undefined;
    this.autoProcess = true;
    this.rankReg = false;
    this.cardIndex = new Array(30);
    for (let i = 0, len = cardInfo.length; i < len; i++) {
      this.cardIndex[i] = i;
    }
    this.cardInfo = JSON.parse(JSON.stringify(cardInfo));
    this.cardInfoScrollOffset = 0;
  }

  resetCardInfo() {
    this.cardIndex = new Array(30);
    for (let i = 0, len = cardInfo.length; i < len; i++) {
      this.cardIndex[i] = i;
    }
    this.cardInfo = JSON.parse(JSON.stringify(cardInfo));
  }

  getRandom() {
    let val1 = Math.floor(Math.random() * 6 + 1);
    let val2 = Math.floor(Math.random() * 6 + 1);
    if (this.isDouble || !this.autoProcess) {
      this.isDouble = false;
    } else {
      this.isDouble = val1 === val2;
      this.diceUse++;
    }
    return val1 + val2;
  }

  getCard(index, pushYN = true) {
    if (index === undefined) {
      if (!this.autoProcess) return;
      var rnd = Math.floor(Math.random() * this.cardIndex.length);
      var index = this.cardIndex[rnd];
    } else {
      if (this.autoProcess) return;
      this.rankReg = true;
      var rnd = this.cardIndex.indexOf(index);
    }
    if (this.cardInfo[index][3] === 0) {
      this.cardIndex.splice(rnd, 1);
    }
    let row = this.cardInfo[index];
    row[3] = 1;
    if (this.cards.length < 5 && pushYN) {
      this.cards.push(row);
    }
    if (this.cardIndex.length === 0) {
      this.resetCardInfo();
    }
  }

  updateScore(value, stop = false) {
    if (stop) value = this.checkStop(value);
    this.score = Math.min(2898, this.score + value);
    this.checkEvent();
  }

  checkStop(value) {
    let startIndex = this.score;
    let endIndex = Math.min(2897, this.score + value - 1);
    for (let i = startIndex; i < endIndex; i++) {
      if (stage[i][5] === 6 || stage[i][5] === 9) {
        value = i - this.score + 1;
        break;
      }
    }
    return value;
  }

  checkEvent() {
    let eventType = stage[this.score - 1][5];
    switch (eventType) {
      case 2:
        this.getCard();
        break;
      case 4:
        this.updateScore(stage[this.score - 1][4], false);
        break;
      default:
        break;
    }
  }

  step(n) {
    if (this.diceUse >= 100 && !this.isDouble) return true;

    if (n === 0) {
      this.updateScore(this.getRandom(), true);
    } else {
      this.useCard(n);
    }

    return this.diceUse >= 100 && !this.isDouble;
  }

  useCard(n) {
    if (n > this.cards.length) return;
    n--;
    let cardType = this.cards[n][1];
    let cardValue = this.cards[n][2];
    this.cards.splice(n, 1);
    switch (cardType) {
      case 1:
        this.updateScore(cardValue, false);
        break;
      case 2:
        this.updateScore(this.getRandom() * cardValue, false);
        break;
      case 3:
        let value = stage[this.score - 1][1] + cardValue;
        for (let i = this.score, len = stage.length - 1; i < len; i++) {
          if (stage[i][1] === value) {
            value = i - this.score + 1;
            break;
          }
        }
        this.updateScore(value, false);
        break;
      default:
        break;
    }
  }

  resetBoard() {
    this.score = 1;
    this.reward = 0;
    this.diceUse = 0;
    this.isDouble = false;
    this.cards = [];
    this.exScores = new Array(6).fill(0);
    this.exScore = Infinity;
    this.exAction = undefined;
    this.rankReg = false;
    this.resetCardInfo();
  }

  getState() {
    return [
      this.rankReg,
      this.autoProcess,
      this.score,
      stage[this.score - 1][1],
      stage[this.score - 1][2],
      this.diceUse,
      this.isDouble ? 1 : 0,
      ...Array(5).fill(0).map((_, i) => this.cards[i] ? this.cards[i][0] : 0),
      ...this.cardInfo.map(card => card[3])
    ];
  }

  setState(state) {
    this.autoProcess = false;
    this.score = state[2];
    this.diceUse = state[5];
    this.isDouble = state[6] === 1;

    this.cards = [];
    for (let i = 7; i < 12; i++) {
      if (state[i] !== 0) {
        this.cards.push(this.cardInfo[state[i] - 1]);
      }
    }

    this.resetCardInfo();
    for (let i = 12; i < 42; i++) {
      if (state[i] === 1) {
        this.getCard(i - 12, false);
      }
    }

    this.rankReg = state[0];
    this.autoProcess = state[1];
  }

  chooseAction() {
    let len = this.cards.length;
    if (len === 0) return 0;

    for (let i = 0; i < len; i++) {
      if (this.cards[i][1] === 1 && this.score + this.cards[i][2] - 1 < 2898 && stage[this.score + this.cards[i][2] - 1][4] > 0 && stage[this.score + this.cards[i][2] + stage[this.score + this.cards[i][2] - 1][4] - 1][5] === 2) {
        return i + 1;
      }
    }

    for (let i = 0; i < len; i++) {
      if (this.cards[i][1] === 1 && this.score + this.cards[i][2] - 1 < 2898 && stage[this.score + this.cards[i][2] - 1][5] === 2) {
        return i + 1;
      }
    }

    for (let i = 0; i < len; i++) {
      if (this.cards[i][1] === 1 && this.score + this.cards[i][2] - 1 < 2898 && stage[this.score + this.cards[i][2] - 1][4] >= 29) {
        return i + 1;
      }
    }

    for (let i = this.score, end = Math.min(2897, this.score + 8); i < end; i++) {
      if (stage[i][5] === 6 || stage[i][5] === 9) {
        for (let j = 0; j < len; j++) {
          if (this.cards[j][1] == 2) return j + 1;
        }
      }
    }

    let cnt = 0;
    for (let i = Math.min(2897, this.score + 1), end = Math.min(2897, this.score + 50); i < end; i++) {
      if (stage[i][1] === stage[this.score - 1][1]) cnt++;
    }

    for (let i = 0; i < len; i++) {
      if (this.cards[i][1] === 3 && cnt >= 26) return i + 1;
    }

    if (len === 5 || this.diceUse + len >= 100) {
      for (let i = 0; i < len; i++) {
        if (this.cards[i][1] === 3 && cnt >= 20) return i + 1;
      }
      for (let i = 0; i < len; i++) {
        if (this.cards[i][1] === 2) return i + 1;
      }
      for (let i = 0; i < len; i++) {
        for (let j = 0; j < len; j++) {
          if (i !== j && this.cards[i][1] === 1 && this.cards[j][1] === 1 && this.score + this.cards[i][2] + this.cards[j][2] - 1 < 2898 && this.score + this.cards[i][2] - 1 < 2898 &&
            (stage[this.score + this.cards[i][2] - 1][4] > 0 && stage[this.score + this.cards[i][2] + this.cards[j][2] - 1][5] === 2)) return i + 1;
        }
      }
      for (let i = 0; i < len; i++) {
        if (this.cards[i][1] === 1 && this.score + this.cards[i][2] - 1 < 2898 && Math.sign(stage[this.score + this.cards[i][2] - 1][4]) !== -1) return i + 1;
      }
      for (let i = 0; i < len; i++) {
        if (this.cards[i][1] !== 1) return i + 1;
      }
    }
    return 0;
  }

  changeMode() {
    this.autoProcess = !this.autoProcess;
    this.rankReg = true;
  }
}

let idx;

onmessage = function (e) {
  idx = e.data.idx;
  stage = e.data.stage;
  cardInfo = e.data.cardInfo;
  state = e.data.state;
  let res = simulation(e.data.iteration, state, e.data.route);
  postMessage({ res, idx, route: e.data.route });
}

function simulation(iteration = 10000, state, route) {
  let env = new Board();
  env.setState(state);
  env.autoProcess = true;
  if (env.diceUse >= 100 && !env.isDouble) return [-2];
  try {
    let actionSize = env.cards.length + 1;
    let avgScores = new Array(actionSize).fill(0);
    let minScores = new Array(actionSize).fill(0);
    let maxScores = new Array(actionSize).fill(0);
    let stdScores = new Array(actionSize).fill(0);
    let medianScores = new Array(actionSize).fill(0);
    for (let i = 0; i < actionSize; i++) {
      let scores = [];
      if (route !== undefined && route.includes(i)) {
        for (let j = 0; j < iteration; j++) {
          let done = false;
          let sEnv = new Board();
          sEnv.setState(state);
          sEnv.autoProcess = true;

          sEnv.step(i);
          while (!done) {
            done = sEnv.step(sEnv.chooseAction());
          }
          scores.push(sEnv.score);
        }
        avgScores[i] = scores.reduce((a, v) => a + v, 0) / scores.length;
        minScores[i] = scores.reduce((min, current) => (current < min ? current : min), scores[0]);
        maxScores[i] = scores.reduce((max, current) => (current > max ? current : max), scores[0]);
        let variance = scores.reduce((a, v) => a + Math.pow(v - avgScores[i], 2), 0) / scores.length;
        stdScores[i] = Math.sqrt(variance);
        let sortedScores = [...scores].sort((a, b) => a - b);
        let median = sortedScores.length % 2 === 0 ? (sortedScores[sortedScores.length / 2 - 1] + sortedScores[sortedScores.length / 2]) / 2 : sortedScores[Math.floor(sortedScores.length / 2)];
        medianScores[i] = median;
      }
    }
    return [1, { avg: avgScores, min: minScores, max: maxScores, std: stdScores, mid: medianScores }];
  } catch (err) {
    console.error(err);
    return [-1];
  }
}
`;

const workerBlob = new Blob([workerCode], { type: 'application/javascript' });
const workerUrl = URL.createObjectURL(workerBlob);
let workers = [];
let workerRunning = new Array(6).fill(false);
let workerIteration = 10000;
let workerReqIndex = 1;

function initWorkers() {
  workers.forEach((w) => w.terminate());
  workers = [];
  for (let i = 0; i < 6; i++) workers.push(new Worker(workerUrl));
}

function addLog(msg) {
  const time = new Date().toLocaleTimeString();
  logLines.push(`[${time}] ${msg}`);
  logLines = logLines.slice(-LOG_LIMIT);
  renderLog();
}

function pushHistory() {
  historyStack.push(env.getState());
  if (historyStack.length > HISTORY_LIMIT) historyStack.shift();
}

function popHistory() {
  if (!historyStack.length) return null;
  return historyStack.pop();
}

function buildLayout() {
  const root = el('root');
  root.innerHTML = `
    <div class="page">
      <div class="col main">
        <div class="card" id="card-summary">
          <div class="card-title">상태</div>
          <div class="grid">
            <div><div class="label">현재 위치</div><div id="summary-position" class="value"></div></div>
            <div><div class="label">현재 스테이지</div><div id="summary-stage" class="value"></div></div>
            <div><div class="label">주사위 사용</div><div id="summary-dice" class="value"></div></div>
            <div><div class="label">모드</div><div id="summary-mode" class="value tag"></div></div>
          </div>
        </div>

        <div class="card" id="card-controls">
          <div class="card-title">이동/주사위</div>
          <div class="grid">
            <div>
              <div class="label">이동 (칸 번호 입력)</div>
              <div class="inline">
                <input type="number" id="input-score" min="1" max="2898" placeholder="예: 120">
                <button id="btn-move" class="primary">이동</button>
              </div>
            </div>
            <div>
              <div class="label">주사위 사용 횟수</div>
              <div class="inline">
                <input type="number" id="input-dice-use" min="0" max="100" placeholder="예: 10">
                <button id="btn-dice-use" class="primary">적용</button>
              </div>
            </div>
          </div>
          <div class="small muted">좌클릭 사용 횟수 증가, 우클릭 미증가(보너스 바로 뒤)</div>
          <div id="dice-buttons"></div>
          <div class="actions">
            <button id="btn-undo">이전으로 되돌리기</button>
            <button id="btn-calc" class="primary">예상 점수 계산</button>
          </div>
        </div>

        <div class="card" id="card-expected">
          <div class="card-title">예상 점수</div>
          <div id="expected-list" class="list"></div>
          <div class="small muted">계산 횟수: <span id="iteration-count"></span></div>
        </div>
      </div>

      <div class="col side">
        <div class="card" id="card-info">
          <div class="card-title">카드 목록</div>
          <div class="actions" style="margin-top:6px; justify-content: flex-end;">
            <span class="label">컬럼:</span>
            <button id="col-2">2</button>
            <button id="col-3">3</button>
            <button id="col-4">4</button>
            <button id="col-5">5</button>
            <button id="btn-compact-mode" class="compact-toggle">축약 모드</button>
          </div>
          <div class="small muted">좌클릭: 획득 표시 · 우클릭: 보유 추가</div>
          <div id="card-info-list" class="list"></div>
        </div>
      </div>
    </div>
  `;
}

function renderAll() {
  renderSummary();
  renderDiceButtons();
  renderExpected();
  renderCardInfo();
}

function renderSummary() {
  const stageId = stage[env.score - 1][1];
  const spaceId = stage[env.score - 1][2];
  el('summary-position').textContent = `${env.score}칸 (스페이스 ${spaceId})`;
  el('summary-stage').textContent = `${stageId}단계 - ${stageNames[stageId - 1]}`;
  el('summary-dice').textContent = `${env.diceUse} / 100`;
  el('summary-mode').textContent = env.autoProcess ? '자동' : '수동';
  el('summary-mode').className = `value tag ${env.autoProcess ? 'tag-blue' : 'tag-orange'}`;
}

function renderDiceButtons() {
  const wrap = el('dice-buttons');
  wrap.innerHTML = '';
  const rows = [
    Array.from({ length: 6 }, (_, i) => i + 2),
    Array.from({ length: 5 }, (_, i) => i + 8),
  ];
  rows.forEach((row, idx) => {
    const rowEl = document.createElement('div');
    rowEl.className = 'dice-row';
    rowEl.style.marginBottom = idx === rows.length - 1 ? '0' : '6px';
    row.forEach((val) => {
      const btn = document.createElement('button');
      btn.textContent = `+${val}`;
      btn.addEventListener('click', () => handleDiceValue(val, true));
      btn.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        handleDiceValue(val, false);
      });
      rowEl.appendChild(btn);
    });
    wrap.appendChild(rowEl);
  });
}

function renderExpected() {
  const list = el('expected-list');
  list.innerHTML = '';

  let bestIdx = typeof env.exAction === 'number' ? env.exAction : null;
  if (bestIdx === null) {
    const numeric = env.exScores
      .map((v, i) => ({ v, i }))
      .filter((x) => typeof x.v === 'number');
    if (numeric.length) {
      const maxVal = Math.max(...numeric.map((x) => x.v));
      const found = numeric.find((x) => x.v === maxVal);
      bestIdx = found ? found.i : null;
    }
  }

  // 주사위 (idx 0)
  const diceRow = document.createElement('div');
  diceRow.className = 'list-row';
  const diceScore = env.exScores ? env.exScores[0] : 0;
  const diceIsNumber = typeof diceScore === 'number';
  const diceExtra = diceIsNumber ? ` (${Math.floor(env.exValues.min[0])} ~ ${Math.floor(env.exValues.max[0])})` : '';
  const diceIsBest = bestIdx === 0;
  const diceTxt = document.createElement('span');
  diceTxt.textContent = `${diceIsBest ? '★ ' : ''}주사위 : ${diceIsNumber ? `${Math.floor(diceScore)}점${diceExtra}` : diceScore}`;
  if (diceIsBest && diceIsNumber) diceTxt.classList.add('text-red');
  diceRow.appendChild(diceTxt);
  list.appendChild(diceRow);

  // 카드 슬롯 1~5 (idx 1~5)
  for (let i = 0; i < 5; i++) {
    const row = document.createElement('div');
    row.className = 'list-row';
    const card = env.cards[i];
    const idx = i + 1;

    if (card) {
      const score = env.exScores ? env.exScores[idx] : 0;
      const isNumber = typeof score === 'number';
      const extra = isNumber ? ` (${Math.floor(env.exValues.min[idx])} ~ ${Math.floor(env.exValues.max[idx])})` : '';
      const isBest = bestIdx === idx;
      const txt = document.createElement('span');
      txt.textContent = `${isBest ? '★ ' : ''}${getCompactCardName(card)} : ${isNumber ? `${Math.floor(score)}점${extra}` : score}`;
      if (isBest && isNumber) txt.classList.add('text-red');
      row.appendChild(txt);

      const btn = document.createElement('button');
      btn.textContent = '사용';
      btn.addEventListener('click', () => handleUseCard(i));
      row.appendChild(btn);
    } else {
      const txt = document.createElement('span');
      txt.textContent = 'N/A : Undefined';
      txt.style.color = '#9ca3af';
      row.appendChild(txt);

      const btn = document.createElement('button');
      btn.textContent = '사용';
      btn.disabled = true;
      btn.style.visibility = 'hidden';
      row.appendChild(btn);
    }

    list.appendChild(row);
  }

  el('iteration-count').textContent = workerIteration.toLocaleString();
}

function renderCards() {
  const container = el('cards-list');
  container.innerHTML = '';
  if (!env.cards.length) {
    container.textContent = '보유 카드가 없습니다.';
    return;
  }
  env.cards.forEach((card, idx) => {
    const row = document.createElement('div');
    row.className = 'list-row';
    const txt = document.createElement('span');
    txt.textContent = `${idx + 1}. ${cardName(card[0])}`;
    const btn = document.createElement('button');
    btn.textContent = '사용';
    btn.addEventListener('click', () => handleUseCard(idx));
    row.appendChild(txt);
    row.appendChild(btn);
    container.appendChild(row);
  });
}

function getCompactCardName(info) {
  const cardType = info[1];
  const cardValue = info[2];
  switch (cardType) {
    case 1: // 칸 이동
      return cardValue >= 0 ? `+${cardValue}` : `${cardValue}`;
    case 2: // 주사위 배수
      return `x${cardValue}`;
    case 3: // 다음 스테이지
      return 'NEXT';
    default:
      return `${info[0]}`;
  }
}

function renderCardInfo() {
  const container = el('card-info-list');
  container.innerHTML = '';

  // 축약 모드 버튼 스타일 업데이트
  const compactBtn = el('btn-compact-mode');
  if (compactBtn) {
    compactBtn.classList.toggle('active', compactMode);
  }

  // 컬럼 버튼 상태 업데이트
  updateColumnButtons();

  env.cardInfo.forEach((info, idx) => {
    const row = document.createElement('div');
    row.className = 'list-row';
    const btn = document.createElement('button');

    // 축약 모드면 축약명, 아니면 기존 형식
    if (compactMode) {
      btn.className = 'compact';
      btn.textContent = getCompactCardName(info);
    } else {
      btn.className = 'wide';
      btn.textContent = `${info[0]}번 - ${cardName(info[0])}`;
    }

    if (info[3] === 1) {
      btn.style.background = '#e5e7eb';
      btn.style.color = '#4b5563';
    } else {
      btn.style.background = '';
      btn.style.color = '';
    }
    btn.addEventListener('click', () => handleCardButton(idx, false));
    btn.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      handleCardButton(idx, true);
    });
    row.appendChild(btn);
    container.appendChild(row);
  });
}

function renderLog() {
  const container = el('log');
  if (!container) return;
  container.innerHTML = '';
  [...logLines].reverse().forEach((line) => {
    const div = document.createElement('div');
    div.textContent = line;
    container.appendChild(div);
  });
}

function formatValue(value) {
  if (typeof value === 'number') return value.toFixed(3);
  return value;
}

function cardName(id) {
  const row = userCardInfo.find((c) => c[0] === id);
  return row ? row[1] : `카드 ${id}`;
}

function handleMoveInput() {
  const n = Number(el('input-score').value);
  if (isNaN(n) || n < 1 || n > 2898) return;
  pushHistory();
  env.score = n;
  env.rankReg = true;
  env.checkEvent();
  addLog(`${n}칸으로 이동했습니다.`);
  renderAll();
  calcEx();
}

function handleDiceUseInput() {
  const n = Number(el('input-dice-use').value);
  if (isNaN(n) || n < 0 || n > 100) return;
  pushHistory();
  env.diceUse = n;
  env.rankReg = true;
  addLog(`주사위 사용 횟수를 ${n}로 설정했습니다.`);
  renderAll();
  calcEx();
}

function handleDiceValue(val, useDice) {
  pushHistory();
  if (useDice) env.diceUse = Math.min(100, env.diceUse + 1);
  env.isDouble = false;
  env.updateScore(val, true);
  addLog(`${useDice ? '주사위를 사용해' : '주사위를 소모하지 않고'} ${val}칸 이동했습니다.`);
  if (env.diceUse >= 100 && useDice) addLog('주사위 사용 100회에 도달했습니다.');
  renderAll();
  calcEx();
}

function handleRandomRoll(useDice) {
  const val = Math.floor(Math.random() * 6 + 1) + Math.floor(Math.random() * 6 + 1);
  handleDiceValue(val, useDice);
}

function handleToggleMode() {
  pushHistory();
  env.changeMode();
  addLog(`모드를 ${env.autoProcess ? '자동' : '수동'}으로 전환했습니다.`);
  renderAll();
}

function handleReset() {
  pushHistory();
  env.resetBoard();
  addLog('보드를 초기화했습니다.');
  renderAll();
  calcEx();
}

function handleUndo() {
  const prev = popHistory();
  if (!prev) {
    addLog('되돌릴 기록이 없습니다.');
    return;
  }
  env.setState(prev);
  addLog('이전 상태로 되돌렸습니다.');
  renderAll();
  calcEx();
}

function handleCardButton(index, addToHand) {
  pushHistory();
  const cardId = env.cardInfo[index][0];
  env.rankReg = true;

  // 좌클릭: 토글 (획득됨 → 미획득)
  if (!addToHand) {
    if (env.cardInfo[index][3] === 1) {
      env.cardInfo[index][3] = 0;
      if (!env.cardIndex.includes(index)) env.cardIndex.push(index);
      env.cards = env.cards.filter((c) => c[0] !== cardId);
      addLog(`${cardName(cardId)}을(를) 미획득으로 돌렸습니다.`);
    } else {
      env.cardInfo[index][3] = 1;
      const idxPos = env.cardIndex.indexOf(index);
      if (idxPos >= 0) env.cardIndex.splice(idxPos, 1);
      addLog(`${cardName(cardId)}을(를) 얻은 적 있음으로 표시했습니다.`);
    }
  } else {
    env.cardInfo[index][3] = 1;
    const idxPos = env.cardIndex.indexOf(index);
    if (idxPos >= 0) env.cardIndex.splice(idxPos, 1);
    const inHand = env.cards.some((c) => c[0] === cardId);
    if (!inHand && env.cards.length < 5) {
      env.cards.push(env.cardInfo[index]);
      addLog(`${cardName(cardId)}을(를) 보유 카드에 추가했습니다.`);
    } else if (inHand) {
      addLog(`${cardName(cardId)}은(는) 이미 보유 중입니다.`);
    } else {
      addLog('보유 슬롯이 가득 찼습니다.');
    }
  }

  if (env.cardIndex.length === 0) env.resetCardInfo();

  renderAll();
  calcEx();
}

function handleUseCard(slotIdx) {
  if (!env.cards[slotIdx]) return;
  pushHistory();
  const name = cardName(env.cards[slotIdx][0]);
  const done = env.step(slotIdx + 1);
  addLog(`${name} 카드를 사용했습니다.`);
  if (done) addLog('주사위 사용 100회에 도달했습니다.');
  renderAll();
  calcEx();
}

function setCardColumns(n) {
  const container = el('card-info-list');
  if (!container) return;
  container.style.setProperty('--card-cols', n);
  currentColumns = n;
  updateColumnButtons();
}

function updateColumnButtons() {
  [2, 3, 4, 5].forEach(n => {
    const btn = el(`col-${n}`);
    if (btn) {
      btn.classList.toggle('active', currentColumns === n);
    }
  });
}

function toggleCompactMode() {
  compactMode = !compactMode;
  if (compactMode) {
    setCardColumns(4);
  } else {
    setCardColumns(2);
  }
  renderCardInfo();
}

function calcEx(r = [0, 1, 2, 3, 4, 5]) {
  env.exScores = new Array(6).fill(0);
  env.exValues = { min: new Array(6).fill(0), max: new Array(6).fill(0), std: new Array(6).fill(0), mid: new Array(6).fill(0) };
  env.exAction = undefined;
  env.exScore = Infinity;

  const reqId = ++workerReqIndex;

  r.forEach((i) => {
    env.exScores[i] = '계산중...';
    if (workerRunning[i]) {
      workers[i].terminate();
      workers[i] = new Worker(workerUrl);
      workerRunning[i] = false;
    }
    workers[i].postMessage({
      idx: reqId,
      iteration: workerIteration,
      state: env.getState(),
      stage: stage,
      cardInfo: cardInfo,
      route: [i], // route는 배열이어야 worker 내부 includes 체크에 대응
    });
    workerRunning[i] = true;

    workers[i].onmessage = function (e) {
      if (e.data.idx !== reqId) return;
      const route = Array.isArray(e.data.route) ? e.data.route[0] : e.data.route;
      if (e.data.res[0] === undefined || e.data.res[0] === -1) {
        env.exScores[route] = 'Error';
        renderExpected();
        return;
      }
      if (e.data.res[0] === -2) {
        env.exScores[route] = env.score;
        renderExpected();
        return;
      }

      workerRunning[route] = false;
      env.exScores[route] = e.data.res[1].avg[route];
      env.exValues.min[route] = e.data.res[1].min[route];
      env.exValues.max[route] = e.data.res[1].max[route];
      env.exValues.mid[route] = e.data.res[1].mid[route];
      env.exValues.std[route] = parseFloat(e.data.res[1].std[route].toFixed(3));

      const finished = env.exScores.every((v) => v !== '계산중...');
      if (finished) {
        const numeric = env.exScores.filter((v) => typeof v === 'number');
        const maxValue = Math.max(...numeric);
        env.exAction = env.exScores.indexOf(maxValue);
        env.exScore = maxValue - calcLoss(workerIteration);
      }
      renderExpected();
    };
  });
  renderExpected();
}

function calcLoss(x) {
  if (x > 999999) return 0;
  const logX = Math.log10(x);
  return 0.25 * Math.pow(logX, 2) - 3.25 * logX + 10.5;
}

function setupEvents() {
  el('btn-move').addEventListener('click', handleMoveInput);
  el('btn-dice-use').addEventListener('click', handleDiceUseInput);
  el('btn-undo').addEventListener('click', handleUndo);
  el('btn-calc').addEventListener('click', () => calcEx());
  el('col-2').addEventListener('click', () => setCardColumns(2));
  el('col-3').addEventListener('click', () => setCardColumns(3));
  el('col-4').addEventListener('click', () => setCardColumns(4));
  el('col-5').addEventListener('click', () => setCardColumns(5));
  el('btn-compact-mode').addEventListener('click', toggleCompactMode);
}

function init() {
  buildLayout();
  initWorkers();
  env = new Board();
  setCardColumns(2);
  setupEvents();
  renderAll();
  calcEx();
}

document.addEventListener('DOMContentLoaded', init);
