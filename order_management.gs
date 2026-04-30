/**
 * 受注管理・分析ツール
 *
 * 概要:
 * 過去データと更新データを比較し、案件の進捗管理と分析を行います。
 *
 * シート構成:
 * 1. 「過去データ」: 前回のスナップショット
 * 2. 「更新データ」: 最新の状況
 * 3. 「分析結果」: 抽出された案件とアドバイスの出力先
 */

/**
 * スプレッドシート起動時にメニューを追加
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('受注管理')
    .addItem('データ分析実行', 'analyzeOrderData')
    .addToUi();
}

function analyzeOrderData() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const pastSheet = ss.getSheetByName('過去データ');
  const currentSheet = ss.getSheetByName('更新データ');

  if (!pastSheet || !currentSheet) {
    SpreadsheetApp.getUi().alert('「過去データ」または「更新データ」シートが見つかりません。');
    return;
  }

  // データの読み込み
  const pastData = getSheetDataAsMap(pastSheet);
  const currentDataList = getSheetDataAsList(currentSheet);

  const results = [];
  const adviceList = [];

  // ヘッダー: 分析結果シート用
  results.push([
    '営業担当者', '取引先名', '案件名', 'ステータス', '確度', '受注予定額', '受注予定年月',
    '変更種別', '変更内容・分析', '改善策・アドバイス'
  ]);

  currentDataList.forEach(current => {
    const key = current['取引先名'] + '_' + current['案件名'];
    const past = pastData[key];

    let changeType = '';
    let analysis = '';
    let advice = '';

    // ③ 更新データの確認（強化項目・停滞懸念）
    if (isStalling(current, past)) {
      changeType = '停滞懸念';
      analysis = 'ステータスに変更がない、または受注予定が先延ばしされています。';
      advice = 'ネクストアクションの再定義と、意思決定者への接触が必要です。';
    }

    // ④ 過去データとの比較（大幅な変更）
    if (past) {
      const changes = getMajorChanges(past, current);
      if (changes.length > 0) {
        changeType = changeType ? changeType + ' / 大幅変更' : '大幅変更';
        analysis += (analysis ? '\n' : '') + '【変更点】' + changes.join('、');
        advice += (advice ? '\n' : '') + generateImprovementPlan(changes, current);
      }
    } else {
      changeType = '新規案件';
      analysis = '新規に投入された案件です。';
      advice = '早期の確度向上に向けたアプローチを開始してください。';
    }

    // ⑤ 確度D/Eの案件へのアドバイス
    if (current['確度'] === 'D' || current['確度'] === 'E') {
      const deAdvice = getLowCertaintyAdvice(current);
      if (deAdvice) {
        analysis += (analysis ? '\n' : '') + '【低確度分析】停滞の可能性あり。';
        advice += (advice ? '\n' : '') + '【D/E対策】' + deAdvice;
      }
    }

    if (changeType) {
      results.push([
        current['営業担当者'],
        current['取引先名'],
        current['案件名'],
        current['ステータス'],
        current['確度'],
        current['受注予定額'],
        current['受注予定年月'],
        changeType,
        analysis,
        advice
      ]);
    }
  });

  // 結果の出力
  outputResults(ss, results);
  SpreadsheetApp.getUi().alert('分析が完了しました。「分析結果」シートを確認してください。');
}

/**
 * シートデータをオブジェクトの配列として取得
 */
function getSheetDataAsList(sheet) {
  const values = sheet.getDataRange().getValues();
  const headers = values.shift();
  return values.map(row => {
    const obj = {};
    headers.forEach((header, index) => {
      obj[header] = row[index];
    });
    return obj;
  });
}

/**
 * シートデータをマップ形式で取得（キー: 取引先名_案件名）
 */
function getSheetDataAsMap(sheet) {
  const list = getSheetDataAsList(sheet);
  const map = {};
  list.forEach(item => {
    const key = item['取引先名'] + '_' + item['案件名'];
    map[key] = item;
  });
  return map;
}

/**
 * 案件が停滞しているか判定
 */
function isStalling(current, past) {
  if (!past) return false;

  // ステータスが変わっていない
  const statusNotChanged = current['ステータス'] === past['ステータス'];

  // 受注予定年月が過去より後ろ倒しになっている
  const currentMonth = new Date(current['受注予定年月']);
  const pastMonth = new Date(past['受注予定年月']);
  const monthDelayed = currentMonth > pastMonth;

  return statusNotChanged && monthDelayed;
}

/**
 * 大幅な変更を抽出
 */
function getMajorChanges(past, current) {
  const changes = [];

  // 確度の変更
  if (past['確度'] !== current['確度']) {
    changes.push(`確度: ${past['確度']} → ${current['確度']}`);
  }

  // 受注予定額の変更（20%以上の変動を大幅とみなす）
  const pastAmount = parseFloat(past['受注予定額']) || 0;
  const currentAmount = parseFloat(current['受注予定額']) || 0;
  if (pastAmount !== 0 && Math.abs((currentAmount - pastAmount) / pastAmount) >= 0.2) {
    changes.push(`金額: ${pastAmount.toLocaleString()} → ${currentAmount.toLocaleString()}`);
  }

  // 受注予定年月の変更
  if (String(past['受注予定年月']) !== String(current['受注予定年月'])) {
    changes.push(`時期: ${past['受注予定年月']} → ${current['受注予定年月']}`);
  }

  return changes;
}

/**
 * 改善策の立案
 */
function generateImprovementPlan(changes, current) {
  let plan = '';
  changes.forEach(change => {
    if (change.includes('確度') && change.includes('→ D') || change.includes('→ E')) {
      plan += '確度低下の要因（競合、予算、決裁フロー）を特定し、カウンタープランを策定してください。';
    } else if (change.includes('金額') && current['受注予定額'] < 1000000) {
      // 例: 金額が下がった場合のアドバイス
      plan += '案件規模縮小の理由を確認し、他部署への横展開やオプション提案を検討してください。';
    } else if (change.includes('時期')) {
      plan += '決定時期がずれた要因を確認し、BANT情報の再徹底を行ってください。';
    }
  });
  return plan || '状況のヒアリングを行い、ボトルネックを解消してください。';
}

/**
 * 低確度案件（D/E）への具体的アドバイス
 */
function getLowCertaintyAdvice(current) {
  const status = current['ステータス'];
  if (status.includes('アプローチ') || status.includes('未着手')) {
    return 'まずはキーマンの特定と、課題のヒアリングに集中してください。';
  } else if (status.includes('提案')) {
    return '提案内容が顧客の経営課題と乖離している可能性があります。仮説構築をやり直してください。';
  }
  return '失注リスクが高いです。リソースの配分を見直すか、上長を交えた戦略会議を実施してください。';
}

/**
 * 結果をシートに出力
 */
function outputResults(ss, results) {
  let resultSheet = ss.getSheetByName('分析結果');
  if (!resultSheet) {
    resultSheet = ss.insertSheet('分析結果');
  } else {
    resultSheet.clear();
  }

  resultSheet.getRange(1, 1, results.length, results[0].length).setValues(results);
  resultSheet.activate();

  // スタイル調整
  resultSheet.getRange(1, 1, 1, results[0].length).setBackground('#f3f3f3').setFontWeight('bold');
  resultSheet.setFrozenRows(1);
}
