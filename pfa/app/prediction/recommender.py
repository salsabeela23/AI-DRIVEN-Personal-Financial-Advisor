import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
import joblib


class AdvancedInvestmentRecommender:
    def __init__(self):
        self.model = RandomForestClassifier(random_state=42)
        self.scaler = StandardScaler()

    def _train_model(self):
        # Extended dataset with more diverse features for better training
        data = pd.DataFrame({
            'total_savings': [100000, 50000, 200000, 150000, 80000, 250000, 300000, 120000, 60000, 40000, 120000, 150000, 180000, 220000, 30000],
            'risk_tolerance': [0.2, 0.5, 0.8, 0.7, 0.3, 0.9, 0.6, 0.5, 0.4, 0.6, 0.5, 0.3, 0.7, 0.8, 0.4],
            'time_horizon': [5, 2, 10, 7, 3, 15, 12, 8, 4, 6, 7, 10, 5, 9, 3],
            'age': [30, 25, 45, 40, 28, 50, 38, 33, 27, 35, 50, 40, 33, 31, 28],
            'income': [70000, 30000, 100000, 75000, 50000, 120000, 150000, 80000, 60000, 45000, 110000, 120000, 80000, 130000, 55000],
            'investment_experience': [1, 0, 3, 2, 1, 4, 3, 2, 1, 2, 4, 3, 2, 3, 1],  # New feature: Investment experience
            'financial_knowledge': [0.7, 0.5, 0.9, 0.8, 0.6, 0.8, 0.7, 0.8, 0.5, 0.7, 0.9, 0.8, 0.6, 0.7, 0.5],  # New feature: Financial knowledge
            'investment_type': [1, 2, 3, 3, 2, 1, 1, 2, 3, 1, 3, 2, 1, 2, 3]  # Target variable
        })

        # Features (X) and Target (y)
        X = data[['total_savings', 'risk_tolerance', 'time_horizon', 'age', 'income', 'investment_experience',
                  'financial_knowledge']]
        y = data['investment_type']

        # Split data into training and testing
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Hyperparameter tuning with GridSearchCV
        param_grid = {
            'n_estimators': [50, 100, 150],
            'max_depth': [5, 10, 15, None],
            'min_samples_split': [2, 5, 10]
        }

        # Reduce n_splits to avoid error if the dataset is small
        grid_search = GridSearchCV(self.model, param_grid, cv=3, n_jobs=-1)
        grid_search.fit(X_train_scaled, y_train)

        # Best model
        self.model = grid_search.best_estimator_

        # Evaluate the model
        y_pred = self.model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        print(f'Model Accuracy: {accuracy * 100:.2f}%')

        # Save the trained model to a file
        joblib.dump(self.model, 'model.pkl')

    def recommend(self, total_savings, risk_tolerance, time_horizon, age, income, investment_experience,
                  financial_knowledge):
        # Load the model from file
        self.model = joblib.load('model.pkl')

        # Map risk_tolerance from 'low', 'medium', 'high' to numerical values
        risk_map = {'low': 0.2, 'medium': 0.5, 'high': 0.8}
        risk_value = risk_map.get(risk_tolerance.lower(), 0.5)

        # Prepare new data for prediction
        X_new = np.array(
            [[total_savings, risk_value, time_horizon, age, income, investment_experience, financial_knowledge]])
        X_new_scaled = self.scaler.transform(X_new)

        # Get prediction (investment type)
        investment_type = self.model.predict(X_new_scaled)[0]
        confidence = self.model.predict_proba(X_new_scaled)[0][investment_type - 1] * 100

        # Map prediction to human-readable recommendations
        investment_map = {1: 'Mutual Funds', 2: 'Fixed Deposits', 3: 'Stocks'}
        recommendation = investment_map.get(investment_type, 'Unknown')

        # Investment advice based on prediction
        advice = self._generate_advice(investment_type, risk_tolerance, investment_experience, financial_knowledge)

        return {
            'recommendation': recommendation,
            'confidence': confidence,
            'advice': advice
        }

    def _generate_advice(self, investment_type, risk_tolerance, investment_experience, financial_knowledge):
        # Sample investment advice
        if investment_type == 1:  # Mutual Funds
            return "Mutual funds are a great option for investors looking for diversification. Since your risk tolerance is {}," \
                   " we recommend focusing on balanced or hybrid funds to minimize volatility.".format(risk_tolerance)
        elif investment_type == 2:  # Fixed Deposits
            return "Fixed Deposits provide stable returns with low risk. Given your risk tolerance and experience, this might be" \
                   " a safe option for you to preserve capital."
        elif investment_type == 3:  # Stocks
            return "Stocks can offer high returns but also come with higher risk. With your experience and risk tolerance, consider" \
                   " investing in blue-chip stocks or ETFs to balance risk and reward."


# Example Usage:
recommender = AdvancedInvestmentRecommender()
recommender._train_model()  # Train the model

# Input Parameters
total_savings = 120000
risk_tolerance = 'medium'
time_horizon = 8
age = 35
income = 75000
investment_experience = 2  # 0 = None, 1 = Beginner, 2 = Intermediate, 3 = Expert
financial_knowledge = 0.7  # Scale 0 to 1

recommendation = recommender.recommend(total_savings, risk_tolerance, time_horizon, age, income, investment_experience,
                                       financial_knowledge)

# Output Recommendation and Advice
print(f'Recommended Investment: {recommendation["recommendation"]}')
print(f'Confidence: {recommendation["confidence"]:.2f}%')
print(f'Investment Advice: {recommendation["advice"]}')
