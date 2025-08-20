import sys

def calculate_dcf(cash_flows, discount_rate, terminal_growth_rate):
    """
    ディスカウンテッド・キャッシュフロー（DCF）を計算します。

    :param cash_flows: list - 将来の予測キャッシュフローのリスト。
    :param discount_rate: float - 割引率（WACCなど）。0から1の間の小数で指定。
    :param terminal_growth_rate: float - ターミナルバリューの永久成長率。0から1の間の小数で指定。
    :return: float - 計算された企業価値（Enterprise Value）。
    """
    if not (0 < discount_rate < 1):
        raise ValueError("割引率は0から1の間の値でなければなりません。")
    if not (0 <= terminal_growth_rate < discount_rate):
        raise ValueError("永久成長率は割引率より低く、0以上でなければなりません。")

    # キャッシュフローの現在価値（PV）を計算
    present_values = []
    for i, cf in enumerate(cash_flows):
        pv = cf / ((1 + discount_rate) ** (i + 1))
        present_values.append(pv)

    present_value_of_cash_flows = sum(present_values)

    # ターミナルバリュー（TV）を計算
    last_cash_flow = cash_flows[-1]
    terminal_value = (last_cash_flow * (1 + terminal_growth_rate)) / (discount_rate - terminal_growth_rate)

    # ターミナルバリューの現在価値を計算
    present_value_of_terminal_value = terminal_value / ((1 + discount_rate) ** len(cash_flows))

    # 企業価値（Enterprise Value）を計算
    enterprise_value = present_value_of_cash_flows + present_value_of_terminal_value

    return enterprise_value

if __name__ == '__main__':
    # --- 入力データ ---
    # 5年間の予測フリーキャッシュフロー（単位：億円）
    future_cash_flows = [100, 110, 120, 130, 140]

    # 割引率（WACC: 加重平均資本コスト）
    wacc = 0.08  # 8%

    # 永久成長率
    perpetual_growth_rate = 0.02  # 2%

    # --- 計算実行 ---
    try:
        ev = calculate_dcf(future_cash_flows, wacc, perpetual_growth_rate)

        # --- 結果表示 ---
        print("--- DCF法による企業価値計算 ---")
        print(f"予測キャッシュフロー: {future_cash_flows}")
        print(f"割引率 (WACC): {wacc:.2%}")
        print(f"永久成長率: {perpetual_growth_rate:.2%}")
        print("-" * 30)
        print(f"企業価値 (Enterprise Value): {ev:,.2f} 億円")
        print("-" * 30)

    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
