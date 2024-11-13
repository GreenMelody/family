document.getElementById('search-button').addEventListener('click', () => {
    const url = document.getElementById('url-input').value;

    fetch('/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: url }),
    })
    .then(response => response.json())
    .then(data => {
        const resultDiv = document.getElementById('result');
        resultDiv.innerHTML = '';

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
                <div class="chart-container">
                    <canvas id="priceChart"></canvas>
                </div>
            `;
            resultDiv.innerHTML = productInfo;

            // Chart.js를 이용해 가격 차트를 생성
            const labels = data.price_history.map(entry => entry.date);
            const originalPrices = data.price_history.map(entry => entry.original_price);
            const employeePrices = data.price_history.map(entry => entry.employee_price);

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
});
