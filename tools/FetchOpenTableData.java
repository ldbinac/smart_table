import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;

/**
 * 模拟第三方应用调用 SmartTable 开放 API（OAuth2 Client Credentials）
 * 拉取指定 Base/Table 的全部记录。
 *
 * 仅作为代码逻辑样例，不依赖任何第三方库，使用 JDK 11+ 标准库 HttpClient。
 * 说明：
 *   - 响应 JSON 的解析用占位方法 parseJsonRecords() 表达，生产环境请接入
 *     Jackson/Gson 等 JSON 库解析出 data 数组与 meta.pagination.total_pages；
 *   - 翻页逻辑完整（while page <= totalPages），样例中 totalPages 从响应 meta 读取。
 *
 * 用法（示例）:
 *   java FetchOpenTableData.java \
 *     --base-id 5e6ab2ad-... \
 *     --table-id d57618ce-... \
 *     --client-id oa_xxx \
 *     --client-secret os_xxx \
 *     [--base-url http://localhost:5000] \
 *     [--page-size 200] \
 *     [--out records.json]
 */
public class FetchOpenTableData {

    // -------------------- 参数模型 --------------------
    static class Args {
        String baseUrl = System.getenv().getOrDefault("SMART_TABLE_BASE_URL", "http://localhost:5000");
        String clientId = System.getenv().getOrDefault("OAUTH_CLIENT_ID", "");
        String clientSecret = System.getenv().getOrDefault("OAUTH_CLIENT_SECRET", "");
        String baseId;
        String tableId;
        int pageSize = 200;
        String outFile;

        static Args parse(String[] argv) {
            Args a = new Args();
            for (int i = 0; i < argv.length; i++) {
                switch (argv[i]) {
                    case "--base-url": a.baseUrl = argv[++i]; break;
                    case "--client-id": a.clientId = argv[++i]; break;
                    case "--client-secret": a.clientSecret = argv[++i]; break;
                    case "--base-id": a.baseId = argv[++i]; break;
                    case "--table-id": a.tableId = argv[++i]; break;
                    case "--page-size": a.pageSize = Integer.parseInt(argv[++i]); break;
                    case "--out": a.outFile = argv[++i]; break;
                    default: throw new IllegalArgumentException("未知参数: " + argv[i]);
                }
            }
            if (a.clientId.isEmpty() || a.clientSecret.isEmpty() || a.baseId == null || a.tableId == null) {
                throw new IllegalArgumentException(
                        "必须提供 --client-id / --client-secret / --base-id / --table-id");
            }
            a.pageSize = Math.min(200, Math.max(1, a.pageSize)); // 服务端上限 200
            return a;
        }
    }

    // -------------------- 客户端封装 --------------------
    private final HttpClient http = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(30)).build();
    private final String baseUrl;
    private String accessToken;

    public FetchOpenTableData(String baseUrl) {
        this.baseUrl = baseUrl;
    }

    /** 发送 JSON 请求，返回响应体字符串；非 2xx 抛异常 */
    private String send(HttpRequest.Builder builder) throws Exception {
        HttpRequest req = builder.build();
        HttpResponse<String> resp = http.send(req, HttpResponse.BodyHandlers.ofString());
        if (resp.statusCode() / 100 != 2) {
            throw new RuntimeException("HTTP " + resp.statusCode() + ": " + resp.body());
        }
        return resp.body();
    }

    /** 换取访问令牌（Basic Auth + grant_type=client_credentials） */
    public String getAccessToken(String clientId, String clientSecret) throws Exception {
        String basic = Base64.getEncoder().encodeToString(
                (clientId + ":" + clientSecret).getBytes(StandardCharsets.UTF_8));
        String body = send(HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/api/oauth/token"))
                .header("Authorization", "Basic " + basic)
                .header("Content-Type", "application/x-www-form-urlencoded")
                .POST(HttpRequest.BodyPublishers.ofString("grant_type=client_credentials")));
        String token = JsonHelper.extractString(body, "access_token");
        if (token == null) {
            throw new RuntimeException("换取令牌失败，响应缺少 access_token: " + body);
        }
        this.accessToken = token;
        return token;
    }

    /** 分页拉取指定表的所有记录 */
    public List<String> fetchAllRecords(String baseId, String tableId, int pageSize) throws Exception {
        List<String> records = new ArrayList<>();
        int page = 1;
        int totalPages = 1;

        do {
            String url = baseUrl + "/api/open/v1/bases/" + baseId + "/tables/" + tableId
                    + "/records?page=" + page + "&per_page=" + pageSize;
            String json = send(HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .header("Authorization", "Bearer " + accessToken)
                    .GET());

            // data: 当前页记录数组；meta.pagination.total_pages: 总页数
            List<String> pageRecords = JsonHelper.parseJsonArray(json, "data");
            records.addAll(pageRecords);
            totalPages = JsonHelper.extractInt(json, "total_pages", totalPages);
            System.out.printf("  第 %d 页: 累计 %d 条%n", page, records.size());

            page++;
        } while (page <= totalPages);

        return records;
    }

    public static void main(String[] args) {
        try {
            Args a = Args.parse(args);
            FetchOpenTableData fetcher = new FetchOpenTableData(a.baseUrl);

            System.out.println("[1/3] 使用 Client Credentials 换取访问令牌 ...");
            fetcher.getAccessToken(a.clientId, a.clientSecret);
            System.out.println("[2/3] 令牌获取成功");

            System.out.println("[3/3] 拉取 base=" + a.baseId + " table=" + a.tableId + " 的全部记录 ...");
            List<String> records = fetcher.fetchAllRecords(a.baseId, a.tableId, a.pageSize);

            System.out.println("完成：共获取 " + records.size() + " 条记录");
            if (!records.isEmpty()) {
                System.out.println("示例（第 1 条）: " + records.get(0));
            }
            if (a.outFile != null) {
                java.nio.file.Files.writeString(
                        java.nio.file.Path.of(a.outFile),
                        "{\"total\":" + records.size() + ",\"records\":" + records + "}",
                        StandardCharsets.UTF_8);
                System.out.println("已导出到: " + a.outFile);
            }
        } catch (Exception e) {
            System.err.println("失败：" + e.getMessage());
            System.exit(1);
        }
    }

    // -------------------- 极简 JSON 工具（样例占位，生产请用 Jackson/Gson） --------------------
    static class JsonHelper {
        /** 提取字符串字段值（含引号自动去除） */
        static String extractString(String json, String field) {
            String key = "\"" + field + "\"";
            int i = json.indexOf(key);
            if (i < 0) return null;
            int colon = json.indexOf(':', i + key.length());
            if (colon < 0) return null;
            int s = skipWs(json, colon + 1);
            if (s >= json.length() || json.charAt(s) != '"') return null;
            StringBuilder sb = new StringBuilder();
            boolean esc = false;
            for (int j = s + 1; j < json.length(); j++) {
                char c = json.charAt(j);
                if (esc) { sb.append(c); esc = false; }
                else if (c == '\\') esc = true;
                else if (c == '"') return sb.toString();
                else sb.append(c);
            }
            return null;
        }

        /** 提取整数字段值 */
        static int extractInt(String json, String field, int def) {
            String key = "\"" + field + "\"";
            int i = json.indexOf(key);
            if (i < 0) return def;
            int colon = json.indexOf(':', i + key.length());
            if (colon < 0) return def;
            int s = skipWs(json, colon + 1);
            int e = s;
            while (e < json.length() && Character.isDigit(json.charAt(e))) e++;
            if (e == s) return def;
            try { return Integer.parseInt(json.substring(s, e)); }
            catch (NumberFormatException ex) { return def; }
        }

        /**
         * 提取 JSON 数组并切分为字符串元素（样例占位实现）。
         * 注意：此处为演示简化，实际应使用 JSON 库解析成对象列表；
         * 本方法假设数组元素均为简单 JSON 对象，按逗号切分后返回原始片段。
         */
        static List<String> parseJsonArray(String json, String field) {
            List<String> out = new ArrayList<>();
            String key = "\"" + field + "\"";
            int i = json.indexOf(key);
            if (i < 0) return out;
            int colon = json.indexOf(':', i + key.length());
            if (colon < 0) return out;
            int s = skipWs(json, colon + 1);
            if (s >= json.length() || json.charAt(s) != '[') return out;
            // 括号配对切分顶层数组元素（忽略嵌套 {} 内的逗号）
            int depth = 0, start = s + 1;
            for (int j = s + 1; j < json.length(); j++) {
                char c = json.charAt(j);
                if (c == '{' || c == '[') depth++;
                else if (c == '}' || c == ']') {
                    if (depth == 0 && c == ']') { // 数组结束
                        if (j > start) out.add(json.substring(start, j).trim());
                        break;
                    }
                    depth--;
                } else if (c == ',' && depth == 0) {
                    out.add(json.substring(start, j).trim());
                    start = j + 1;
                }
            }
            return out;
        }

        private static int skipWs(String json, int i) {
            while (i < json.length() && Character.isWhitespace(json.charAt(i))) i++;
            return i;
        }
    }
}
