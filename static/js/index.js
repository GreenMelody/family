document.addEventListener("DOMContentLoaded", () => {
    const today = new Date();
    const fifteenDaysAgo = new Date();
    fifteenDaysAgo.setDate(today.getDate() - 15);

    const formatDate = (date) => {
        const yyyy = date.getFullYear();
        const mm = String(date.getMonth() + 1).padStart(2, "0");
        const dd = String(date.getDate()).padStart(2, "0");
        return `${yyyy}-${mm}-${dd}`;
    };

    const formatDateTime = (dateTimeStr) => {
        const date = new Date(dateTimeStr);
        const yyyy = date.getFullYear();
        const mm = String(date.getMonth() + 1).padStart(2, "0");
        const dd = String(date.getDate()).padStart(2, "0");
        const hh = String(date.getHours()).padStart(2, "0");
        const min = String(date.getMinutes()).padStart(2, "0");
        const sec = String(date.getSeconds()).padStart(2, "0");
        return `${yyyy}-${mm}-${dd} ${hh}:${min}:${sec}`;
    };

    let chartInstance = null;

    const searchHandler = async () => {
        const url = document.getElementById("urlInput").value.trim();
        if (!url) {
            alert("상품 페이지 URL을 입력해주세요.");
            return;
        }
        const response = await fetch(`/api/url-status?url=${encodeURIComponent(url)}`);
        const data = await response.json();

        const resultDiv = document.getElementById("result");
        resultDiv.innerHTML = ""; // 기존 내용 초기화

        if (data.status === "active") {
            const formattedStartDate = formatDateTime(data.start_date);

            resultDiv.innerHTML = `
                <p><strong>해당 URL은 ${formattedStartDate}부터 데이터 수집 중입니다.<strong></p>
                <div class="row">
                    <!-- 왼쪽 열 -->
                    <div class="col-md-6 text-start">
                        <p><strong>상품명:</strong> ${data.product_name}</p>
                        <p><strong>모델명:</strong> ${data.model_name}</p>
                        <p><strong>옵션:</strong> ${data.options}</p>
                        <p><strong>상품페이지: </strong><a href="${data.product_url}" target="_blank">바로가기</a></p>
                    </div>
                    <!-- 오른쪽 열 -->
                    <div class="col-md-6 text-center">
                        <a href="${data.image_url}" target="_blank">
                            <img src="${data.image_url}" alt="Product Image" class="img-fluid rounded">
                        </a>
                    </div>
                </div>

                <div class="mt-4">
                    <label for="startDate">시작</label>
                    <input type="date" id="startDate" value="${formatDate(fifteenDaysAgo)}">
                    <label for="endDate">종료</label>
                    <input type="date" id="endDate" value="${formatDate(today)}">
                    <button class="btn btn-secondary" id="filterButton">검색</button>
                </div>

                <canvas id="priceChart" class="mt-4"></canvas>
                <table class="table mt-4">
                    <thead>
                        <tr>
                            <th>날짜</th>
                            <th>출고가</th>
                            <th>임직원가</th>
                        </tr>
                    </thead>
                    <tbody id="priceTableBody"></tbody>
                </table>
            `;
            resultDiv.style.display = "block";

            updateGraph(data.prices);
            updateTable(data.prices);

            document.getElementById("filterButton").addEventListener("click", async () => {
                const startDate = document.getElementById("startDate").value;
                const endDate = document.getElementById("endDate").value;

                if (!startDate || !endDate || new Date(startDate) > new Date(endDate)) {
                    alert("올바른 시작 날짜와 종료 날짜를 선택해주세요.");
                    return;
                }

                const filterResponse = await fetch(
                    `/api/url-data?url=${encodeURIComponent(url)}&start_date=${startDate}&end_date=${endDate}`
                );
                const filterData = await filterResponse.json();

                if (filterData.status === "success") {
                    updateGraph(filterData.prices);
                    updateTable(filterData.prices);
                } else {
                    alert("데이터를 가져오는 데 실패했습니다.");
                }
            });
        } else {
            resultDiv.innerHTML = `
                <p>${data.message}</p>
            `;
            resultDiv.style.display = "block";
        }
    };

    // 검색 버튼 클릭 이벤트
    document.getElementById("searchButton").addEventListener("click", searchHandler);

    // URL 파라미터에서 URL 검색
    const params = new URLSearchParams(window.location.search);
    const urlParam = params.get("url");
    if (urlParam) {
        document.getElementById("urlInput").value = urlParam;
        searchHandler(); // 자동으로 검색 수행
    }

    // 검색창 Enter 키 이벤트 추가
    document.getElementById("urlInput").addEventListener("keypress", (event) => {
        if (event.key === "Enter") {
            event.preventDefault(); // 기본 Enter 동작 방지
            searchHandler(); // 검색 버튼과 동일한 동작 실행
        }
    });

    // 검색창 포커스 시 텍스트 전체 선택
    document.getElementById("urlInput").addEventListener("focus", (event) => {
        event.target.select();
    });

    // 브라우저 크기 변경 시 차트 리사이즈
    window.addEventListener("resize", () => {
        if (chartInstance) {
            chartInstance.resize();
        }
    });

    function updateGraph(prices) {
        const resultDiv = document.getElementById("result");
        if (!prices || prices.length === 0) {
            resultDiv.innerHTML += "<p>표시할 데이터가 없습니다.</p>";
            return;
        }

        const ctx = document.getElementById("priceChart").getContext("2d");

        // 기존 차트 초기화
        if (chartInstance) {
            chartInstance.destroy();
        }

        // 새 차트 생성
        chartInstance = new Chart(ctx, {
            type: "line",
            data: {
                labels: prices.map((price) => price.date),
                datasets: [
                    {
                        label: "출고가",
                        data: prices.map((price) => price.release_price),
                        borderColor: "#FF5733", // 밝은 주황색
                        backgroundColor: "rgba(255, 87, 51, 0.2)", // 투명 주황색
                        borderWidth: 2,
                        pointBackgroundColor: "#FF5733",
                        pointBorderColor: "#FF5733",
                        pointRadius: 5, // 데이터 포인트 크기
                    },
                    {
                        label: "임직원가",
                        data: prices.map((price) => price.employee_price),
                        borderColor: "#28A745", // 밝은 녹색
                        backgroundColor: "rgba(40, 167, 69, 0.2)", // 투명 녹색
                        borderWidth: 2,
                        pointBackgroundColor: "#28A745",
                        pointBorderColor: "#28A745",
                        pointRadius: 5, // 데이터 포인트 크기
                    },
                ],
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: true,
                        labels: {
                            color: "#FFFFFF", // 범례 텍스트 흰색
                        },
                    },
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: "날짜",
                            color: "#FFFFFF", // x축 제목 흰색
                        },
                        ticks: {
                            color: "#FFFFFF", // x축 눈금 흰색
                        },
                        grid: {
                            color: "rgba(255, 255, 255, 0.2)", // x축 그리드 라인
                        },
                    },
                    y: {
                        title: {
                            display: true,
                            text: "가격",
                            color: "#FFFFFF", // y축 제목 흰색
                        },
                        ticks: {
                            color: "#FFFFFF", // y축 눈금 흰색
                        },
                        grid: {
                            color: "rgba(255, 255, 255, 0.2)", // y축 그리드 라인
                        },
                    },
                },
                layout: {
                    padding: 20, // 차트 내부 여백
                },
            },
        });
    }

    function updateTable(prices) {
        const tableBody = document.getElementById("priceTableBody");
        tableBody.innerHTML = prices
            .map(
                (price) => `
                <tr>
                    <td>${price.date}</td>
                    <td>${price.release_price}</td>
                    <td>${price.employee_price}</td>
                </tr>
            `
            )
            .join("");
    }
});
