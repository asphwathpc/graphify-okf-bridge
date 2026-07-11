Output hero.gif

Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 640
Set Theme "Dracula"
Set Padding 20
Set TypingSpeed 40ms

Type `# jaffle-shop (dbt) + GA4, merged into one graph by graphify-okf-bridge`
Enter
Sleep 800ms

Type `graphify path "stg_orders.sql" "orders" --graph .demo-out/merged.json`
Enter
Sleep 3s

Type `graphify explain "orders" --graph .demo-out/merged.json`
Enter
Sleep 4s
