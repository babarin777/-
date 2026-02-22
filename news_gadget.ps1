# 依存ライブラリ不要のWindows用ニュースガジェット (PowerShell版)
Add-Type -AssemblyName PresentationFramework, PresentationCore, WindowsBase, System.Windows.Forms

# --- 社内網・セキュリティ対策設定 ---
# モダンなTLSプロトコルを強制
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12, [System.Net.SecurityProtocolType]::Tls11, [System.Net.SecurityProtocolType]::Tls

# システムプロキシの利用設定をプロセス全体に適用
[System.Net.WebRequest]::DefaultWebProxy = [System.Net.WebRequest]::GetSystemWebProxy()
[System.Net.WebRequest]::DefaultWebProxy.Credentials = [System.Net.CredentialCache]::DefaultCredentials

# SSL証明書の検証エラーを無視する設定（社内網でのSSLインターセプト対策）
if (-not ("TrustAllCertsPolicy" -as [type])) {
    Add-Type -TypeDefinition @"
    using System.Net;
    using System.Security.Cryptography.X509Certificates;
    public class TrustAllCertsPolicy : ICertificatePolicy {
        public bool CheckValidationResult(ServicePoint srvPoint, X509Certificate certificate, WebRequest request, int certificateProblem) {
            return true;
        }
    }
"@
    [System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy
}

$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="News Gadget" Height="700" Width="500" Background="White"
        FontFamily="Meiryo UI">
    <Grid>
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
            <RowDefinition Height="Auto"/>
        </Grid.RowDefinitions>

        <Button Name="BtnRefresh" Content="ニュースを更新" Margin="10" Padding="10"
                FontFamily="Meiryo UI" FontSize="14" FontWeight="Bold"/>

        <TabControl Name="Tabs" Grid.Row="1" Margin="10,0,10,10" FontFamily="Meiryo UI">
            <TabItem Header="AI関連" Name="TabAI">
                <ScrollViewer VerticalScrollBarVisibility="Auto">
                    <StackPanel Name="PanelAI" Background="#F0F8FF" Padding="10"/>
                </ScrollViewer>
            </TabItem>
            <TabItem Header="再エネ" Name="TabRE">
                <ScrollViewer VerticalScrollBarVisibility="Auto">
                    <StackPanel Name="PanelRE" Background="#FFF0F5" Padding="10"/>
                </ScrollViewer>
            </TabItem>
            <TabItem Header="EV" Name="TabEV">
                <ScrollViewer VerticalScrollBarVisibility="Auto">
                    <StackPanel Name="PanelEV" Background="#F0FFF0" Padding="10"/>
                </ScrollViewer>
            </TabItem>
        </TabControl>

        <TextBlock Grid.Row="2" Text="※表示されない場合はネット接続を確認してください"
                   HorizontalAlignment="Center" Margin="5" Foreground="Gray" FontSize="10" FontFamily="Meiryo UI"/>
    </Grid>
</Window>
"@

$reader = [System.Xml.XmlReader]::Create([System.IO.StringReader]::New($xaml))
$window = [System.Windows.Markup.XamlReader]::Load($reader)

$btnRefresh = $window.FindName("BtnRefresh")
$panelAI = $window.FindName("PanelAI")
$panelRE = $window.FindName("PanelRE")
$panelEV = $window.FindName("PanelEV")

# ユーティリティ: UrlEncode用の型
if (-not ("Main.Web" -as [type])) {
    Add-Type -TypeDefinition @"
    using System;
    using System.Net;
    namespace Main {
        public class Web {
            public static string UrlEncode(string text) {
                return WebUtility.UrlEncode(text);
            }
        }
    }
"@
}

function Get-News {
    param($query)
    $encoded = [Main.Web]::UrlEncode($query)
    # ブラウザでの直接検索に近い形式のURL
    $url = "https://news.google.com/search?q=$encoded&hl=ja&gl=JP&ceid=JP:ja&output=rss"

    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    # プロキシで現在のユーザーの認証情報を使用する
    $session.ProxyUseDefaultCredentials = $true

    $cookie = New-Object System.Net.Cookie("CONSENT", "YES+", "/", ".google.com")
    $session.Cookies.Add($cookie)

    $headers = @{
        "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        "Accept-Language" = "ja,en-US;q=0.9,en;q=0.8"
        "Referer" = "https://news.google.com/"
    }

    try {
        $global:LastPsError = $null
        $response = Invoke-WebRequest -Uri $url -WebSession $session -Headers $headers -TimeoutSec 15 -UseBasicParsing

        $content = $response.Content
        if ($content -like "*<html*" -or $content -like "*<!doctype html*") {
            $global:LastPsError = "社内のURLフィルタリングによりRSSが遮断されました。"
            return @()
        }

        [xml]$xml = $content
        $items = $xml.rss.channel.item
        if ($null -eq $items) {
            $snippet = $content.Substring(0, [Math]::Min(100, $content.Length)).Replace("`n", " ")
            $global:LastPsError = "記事データが見つかりません。(冒頭: $snippet...)"
            return @()
        }

        $all = @()
        foreach ($item in $items) {
            $pubDate = [datetime]$item.pubDate
            # sourceがオブジェクトか文字列か判定してテキストを取得
            $sourceText = if ($item.source -is [System.Management.Automation.PSCustomObject]) { $item.source."#text" } else { $item.source }
            if ($null -eq $sourceText) { $sourceText = "不明" }

            $all += [PSCustomObject]@{
                Title = $item.title
                Link = $item.link
                Source = $sourceText
                Date = $pubDate
                IsNikkei = $sourceText -like "*日本経済新聞*"
            }
        }

        $all = $all | Sort-Object Date -Descending
        $nikkei = $all | Where-Object IsNikkei
        $others = $all | Where-Object { -not $_.IsNikkei }

        $priority = $nikkei | Select-Object -First 3
        $rest = ($nikkei | Select-Object -Skip 3) + $others | Sort-Object Date -Descending

        return ($priority + $rest) | Select-Object -First 20
    } catch {
        $global:LastPsError = $_.Exception.Message
        return @()
    }
}

function Render-Category {
    param($panel, $items)
    $panel.Children.Clear()
    if ($null -eq $items -or $items.Count -eq 0) {
        $err = New-Object System.Windows.Controls.TextBlock
        $msg = "記事を取得できませんでした"
        if ($global:LastPsError) { $msg += "`n`n詳細: " + $global:LastPsError }
        $err.Text = $msg
        $err.Margin = "50"
        $err.TextAlignment = "Center"
        $err.HorizontalAlignment = "Center"
        $panel.Children.Add($err)
        return
    }

    foreach ($item in $items) {
        $border = New-Object System.Windows.Controls.Border
        $border.Background = [System.Windows.Media.Brushes]::White
        $border.BorderBrush = [System.Windows.Media.Brushes]::LightGray
        $border.BorderThickness = "1"
        $border.CornerRadius = "5"
        $border.Margin = "0,0,0,10"
        $border.Padding = "10"

        $stack = New-Object System.Windows.Controls.StackPanel

        if ($item.IsNikkei) {
            $badge = New-Object System.Windows.Controls.TextBlock
            $badge.Text = "日経新聞"
            $badge.Background = [System.Windows.Media.BrushConverter]::new().ConvertFrom("#003399")
            $badge.Foreground = [System.Windows.Media.Brushes]::White
            $badge.FontSize = 10
            $badge.Padding = "4,1"
            $badge.HorizontalAlignment = "Left"
            $badge.Margin = "0,0,0,5"
            $stack.Children.Add($badge)
        }

        $title = New-Object System.Windows.Controls.TextBlock
        $title.Text = $item.Title
        $title.TextWrapping = "Wrap"
        $title.FontSize = 14
        $title.FontWeight = "Bold"
        $title.Cursor = [System.Windows.Input.Cursors]::Hand
        if ($item.IsNikkei) { $title.Foreground = [System.Windows.Media.Brushes]::Black }
        else { $title.Foreground = [System.Windows.Media.BrushConverter]::new().ConvertFrom("#0000EE") }

        # クロージャを使用して変数を固定する
        $currentLink = $item.Link
        $title.add_MouseDown({
            param($s, $e)
            Start-Process $currentLink
        }.GetNewClosure())

        $title.add_MouseEnter({ $title.TextDecorations = [System.Windows.TextDecorations]::Underline })
        $title.add_MouseLeave({ $title.TextDecorations = $null })

        $stack.Children.Add($title)

        $info = New-Object System.Windows.Controls.TextBlock
        $info.Text = "$($item.Source) | $($item.Date.ToString('yyyy/MM/dd HH:mm'))"
        $info.Foreground = [System.Windows.Media.Brushes]::Gray
        $info.FontSize = 11
        $info.Margin = "0,5,0,0"
        $stack.Children.Add($info)

        $border.Child = $stack
        $panel.Children.Add($border)
    }
}

function Update-UI {
    $btnRefresh.IsEnabled = $false
    $panelAI.Children.Clear()
    $panelRE.Children.Clear()
    $panelEV.Children.Clear()

    $loadingText = "取得中..."
    @( $panelAI, $panelRE, $panelEV ) | ForEach-Object {
        $loading = New-Object System.Windows.Controls.TextBlock
        $loading.Text = $loadingText
        $loading.Margin = "50"
        $loading.HorizontalAlignment = "Center"
        $_.Children.Add($loading)
    }

    # UIを更新するためにDoEventsを呼び出す
    [System.Windows.Forms.Application]::DoEvents()

    # ニュース取得 (順次実行)
    $resAI = Get-News "人工知能 OR 生成AI OR AI"
    Render-Category $panelAI $resAI
    [System.Windows.Forms.Application]::DoEvents()

    $resRE = Get-News "再生可能エネルギー OR 再エネ OR 太陽光 OR 風力"
    Render-Category $panelRE $resRE
    [System.Windows.Forms.Application]::DoEvents()

    $resEV = Get-News "電気自動車 OR EV OR テスラ OR 自動運転"
    Render-Category $panelEV $resEV

    $btnRefresh.IsEnabled = $true
}

$btnRefresh.add_Click({ Update-UI })
$window.add_Loaded({ Update-UI })
$window.ShowDialog() | Out-Null
