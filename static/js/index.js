// 날짜를 포맷팅하는 함수
function formatDate(date) {
    const year = date.getFullYear();
    const month = ('0' + (date.getMonth() + 1)).slice(-2);
    const day = ('0' + date.getDate()).slice(-2);
    return `${year}-${month}-${day}`;
}

// 시작, 종료 날짜 초기화
const today = new Date();
const endDateInput = document.createElement('input');
const startDateInput = document.createElement('input');
endDateInput.type = startDateInput.type = 'date';
endDateInput.value = formatDate(today);
startDateInput.value = formatDate(new Date(today.setDate(today.getDate() - 15)));

// 그래프를 그리는 함수
function drawChart(labels, originalPrices, employeePrices) {
    const ctx = document.getElementById('priceChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '출고가',
                    data: originalPrices,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    fill: false
                },
                {
                    label: '임직원가',
                    data: employeePrices,
                    borderColor: 'rgba(153, 102, 255, 1)',
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: '가격 변동 차트'
                }
            }
        }
    });
}

// 검색 버튼 클릭 이벤트
document.getElementById('search-button').addEventListener('click', () => {
    searchProduct();
});

// URL 입력창에서 엔터키를 눌렀을 때 검색
document.getElementById('url-input').addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        event.preventDefault(); // 기본 폼 제출 방지
        document.getElementById('search-button').click(); // 검색 버튼 클릭 트리거
    }
});

// 상품 검색 및 차트 업데이트 함수
// 상품 검색 및 차트 업데이트 함수
function searchProduct() {
    const url = document.getElementById('url-input').value;
    const startDate = document.getElementById('start-date') ? document.getElementById('start-date').value : startDateInput.value;
    const endDate = document.getElementById('end-date') ? document.getElementById('end-date').value : endDateInput.value;

    fetch('/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: url, start_date: startDate, end_date: endDate }),
    })
    .then(response => response.json())
    .then(data => {
        const resultDiv = document.getElementById('result');
        const statusMessageDiv = document.getElementById('status-message');
        resultDiv.innerHTML = '';
        statusMessageDiv.innerHTML = '';

        // 상태 메시지 업데이트
        if (data.status_message) {
            statusMessageDiv.textContent = data.status_message;
        }

        if (data.exists) {
            const product = data.product;
            const productInfo = `
                <div class="product-info">
                    <div class="product-details">
                        <p><strong>상품명:</strong> ${product.name}</p>
                        <p><strong>모델명:</strong> ${product.model}</p>
                        <p><strong>옵션:</strong> ${product.options}</p>
                        <p><strong>상품페이지:</strong> <a href="${product.url}" target="_blank">바로가기</a></p>
                    </div>
                    <div class="product-image">
                        <img src="${product.image_url}" alt="Product Image" />
                    </div>
                </div>
                <div class="date-controls">
                    <label>시작:</label>
                    <input type="date" id="start-date" value="${startDate}">
                    <label>종료:</label>
                    <input type="date" id="end-date" value="${endDate}">
                    <button id="date-search-button">검색</button>
                </div>
                <div class="chart-container">
                    <canvas id="priceChart"></canvas>
                </div>
            `;
            resultDiv.innerHTML = productInfo;

            // date-search-button이 생성된 이후 이벤트 리스너 등록
            document.getElementById('date-search-button').addEventListener('click', () => {
                searchProduct();
            });

            const labels = data.price_history.map(entry => entry.date);
            const originalPrices = data.price_history.map(entry => entry.original_price);
            const employeePrices = data.price_history.map(entry => entry.employee_price);

            drawChart(labels, originalPrices, employeePrices);
        } else {
            if (confirm(data.message)) {
                fetch('/collect_data', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ url: url }),
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                });
            }
        }
    });
}
