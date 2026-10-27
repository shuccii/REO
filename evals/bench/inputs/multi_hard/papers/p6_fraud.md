# Gradient boosting for credit-card fraud detection (fictional abstract)

We trained a gradient-boosting classifier on 284,000 credit-card transactions, of which 0.9% were fraudulent. The data were split chronologically: the first nine months for training and the last three months for testing, so that no future information was used. Hyperparameters were tuned with cross-validation inside the training period. On the test period, the model achieved an accuracy of 99.1%. We conclude that the model detects fraud reliably and is ready for deployment.
