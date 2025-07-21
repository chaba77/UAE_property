package main

import (
	"bytes"
	"crypto/tls"
	"fmt"
	"io/ioutil"
	"net/http"
	"strconv"
	"strings"
	"sync"
)

func main() {
	headers := map[string]string{
		"Host":               "www.propertyfinder.ae",
		"X-Nextjs-Data":      "1",
		"Sec-Ch-Ua-Platform": "\"Linux\"",
		"Accept-Language":    "en-US,en;q=0.9",
		"Sec-Ch-Ua":          "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\"",
		"User-Agent":         "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
		"Sec-Ch-Ua-Mobile":   "?0",
		"Accept":             "*/*",
		"Sec-Fetch-Site":     "same-origin",
		"Sec-Fetch-Mode":     "cors",
		"Sec-Fetch-Des":      "empty",
		"Priority":           "u=1, i",
	}

	var data = []byte(nil)
	concurrencyLimit := 20
	sem := make(chan struct{}, concurrencyLimit)

	type result struct {
		Number   int
		FullName string
	}

	results := make(chan result, 1000)
	var wg sync.WaitGroup

	for i := 1; i<9; i++ {
		wg.Add(1)
		sem <- struct{}{}

		go func(i int) {
			defer wg.Done()
			defer func() { <-sem }()

			url := "https://www.propertyfinder.ae:443/search/_next/data/OJefluvpw_53_FSTVIQCT/en/search.json?l=" + strconv.Itoa(i) + "&c=2&fu=0&rp=y&ob=mr"
			status, body := httpRequest(url, "GET", data, headers)

			if status != "200 OK" {
				return
			}

			// Count number of appearances of: {"title":"Properties for rent
			count := strings.Count(body, `{"title":"Properties for rent`)
			if count == 2 {
				name := extractLocationTitle(body)
				fmt.Printf("FOUND [%d %s]\n", i, name)
				results <- result{Number: i, FullName: name}
			} else if count > 2 {
				fmt.Printf("NOT FOUND [%d]\n", i)
			}
		}(i)
	}

	go func() {
		wg.Wait()
		close(results)
	}()

	var workingEndpoints [][]string
	for res := range results {
		workingEndpoints = append(workingEndpoints, []string{strconv.Itoa(res.Number), res.FullName})
	}

	fmt.Println("✅ Final Working Endpoints:")
	for _, item := range workingEndpoints {
		fmt.Println(item)
	}
}

func httpRequest(targetUrl string, method string, data []byte, headers map[string]string) (string, string) {
	request, err := http.NewRequest(method, targetUrl, bytes.NewBuffer(data))
	if err != nil {
		fmt.Println("Request failed:", err)
		return "", ""
	}

	for k, v := range headers {
		request.Header.Set(k, v)
	}

	customTransport := &http.Transport{
		TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
	}
	client := &http.Client{Transport: customTransport}
	response, err := client.Do(request)
	if err != nil {
		fmt.Println("Request failed:", err)
		return "", ""
	}
	defer response.Body.Close()

	bodyBytes, err := ioutil.ReadAll(response.Body)
	if err != nil {
		return response.Status, ""
	}
	return response.Status, string(bodyBytes)
}

// extractLocationTitle extracts the name between `{"title":"Properties for rent ` and `","path":"`
func extractLocationTitle(body string) string {
	start := `{"title":"Properties for rent `
	end := `","path":"`

	startIdx := strings.Index(body, start)
	if startIdx == -1 {
		return ""
	}
	startIdx += len(start)
	endIdx := strings.Index(body[startIdx:], end)
	if endIdx == -1 {
		return ""
	}
	return body[startIdx : startIdx+endIdx]
}
