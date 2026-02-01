"""
AI 预测模型
"""
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import torch
import torch.nn as nn

class LSTMModel(nn.Module):
    def __init__(self, input_size=1, hidden_size=64, num_layers=2):
        super(LSTMModel, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)
    
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out

class AIPredictor:
    def __init__(self):
        self.model = None
        self.scaler = MinMaxScaler()
    
    def prepare_data(self, prices, seq_length=10):
        """准备训练数据"""
        scaled_data = self.scaler.fit_transform(np.array(prices).reshape(-1, 1))
        
        X, y = [], []
        for i in range(len(scaled_data) - seq_length):
            X.append(scaled_data[i:i+seq_length])
            y.append(scaled_data[i+seq_length])
        
        return np.array(X), np.array(y)
    
    def train(self, prices, epochs=100):
        """训练模型"""
        X, y = self.prepare_data(prices)
        
        if len(X) == 0:
            return {"error": "Not enough data"}
        
        self.model = LSTMModel()
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        
        X_tensor = torch.FloatTensor(X)
        y_tensor = torch.FloatTensor(y)
        
        for epoch in range(epochs):
            self.model.train()
            optimizer.zero_grad()
            output = self.model(X_tensor)
            loss = criterion(output, y_tensor)
            loss.backward()
            optimizer.step()
        
        return {"status": "trained", "epochs": epochs}
    
    def predict(self, prices):
        """预测"""
        if self.model is None:
            # 简单移动平均预测
            return {"prediction": np.mean(prices[-5:]), "method": "ma"}
        
        self.model.eval()
        with torch.no_grad():
            scaled_data = self.scaler.transform(np.array(prices[-10:]).reshape(-1, 1))
            X = torch.FloatTensor(scaled_data).unsqueeze(0)
            pred = self.model(X)
            prediction = self.scaler.inverse_transform(pred.numpy())[0][0]
        
        return {"prediction": prediction, "method": "lstm"}

if __name__ == "__main__":
    predictor = AIPredictor()
    # 模拟数据测试
    test_prices = [100 + i + np.random.randn() for i in range(50)]
    print(predictor.train(test_prices))
    print(predictor.predict(test_prices))
