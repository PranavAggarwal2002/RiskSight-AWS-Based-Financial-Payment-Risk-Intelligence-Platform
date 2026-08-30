import React, { useState } from 'react';
import './PaymentRequestForm.css';

const PaymentRequestForm = ({ user }) => {
  const [formData, setFormData] = useState({
    vendorId: user?.vendor_id || '',
    accountId: '',
    amount: '',
    timeStamp: new Date().toISOString().slice(0, 16),
    location: ''
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    console.log("Submitting Payment Request:", formData);

    try {
      const response = await fetch('/api/payment-request', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          vendor_id: formData.vendorId,
          account_id: formData.accountId,
          amount: parseFloat(formData.amount),
          timestamp: new Date(formData.timeStamp).toISOString(),
          location: formData.location
        }),
      });

      if (response.ok) {
        alert('Payment request submitted successfully!');
        setFormData({
          vendorId: user?.vendor_id || '',
          accountId: '',
          amount: '',
          timeStamp: new Date().toISOString().slice(0, 16),
          location: ''
        });
      } else {
        const error = await response.json().catch(() => ({}));
        alert(`Error: ${error.message || 'Something went wrong'}`);
      }
    } catch (error) {
      console.error("Error submitting form:", error);
      alert('Failed to connect to the server.');
    }
  };

  return (
    <div className="payment-form-container">
      <div className="payment-form-header">
        <h2>Submit Payment Request</h2>
        <p>Enter the transaction details securely below.</p>
      </div>

      <form className="apple-style-form" onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="vendorId">Vendor ID</label>
          <input
            type="text"
            id="vendorId"
            name="vendorId"
            className="form-input"
            value={formData.vendorId}
            onChange={handleChange}
            placeholder="e.g. VEND-8492"
            required
            disabled={user?.role === 'client'}
            readOnly={user?.role === 'client'}
          />
        </div>

        <div className="form-group">
          <label htmlFor="accountId">Account ID</label>
          <input
            type="text"
            id="accountId"
            name="accountId"
            className="form-input"
            value={formData.accountId}
            onChange={handleChange}
            placeholder="e.g. ACC-10934"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="amount">Amount (USD)</label>
          <input
            type="number"
            id="amount"
            name="amount"
            className="form-input"
            value={formData.amount}
            onChange={handleChange}
            placeholder="0.00"
            min="0"
            step="0.01"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="timeStamp">Time Stamp</label>
          <input
            type="datetime-local"
            id="timeStamp"
            name="timeStamp"
            className="form-input"
            value={formData.timeStamp}
            onChange={handleChange}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="location">Location (City)</label>
          <input
            type="text"
            id="location"
            name="location"
            className="form-input"
            value={formData.location}
            onChange={handleChange}
            placeholder="e.g. Mumbai"
            required
          />
        </div>

        <button type="submit" className="submit-btn">
          Submit Request
        </button>
      </form>
    </div>
  );
};

export default PaymentRequestForm;
