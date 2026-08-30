import React, { useState, useEffect } from 'react';
import './ApprovalWorkflow.css';

const ApprovalWorkflow = ({ user }) => {
  const [pendingRequests, setPendingRequests] = useState([]);

  useEffect(() => {
    const fetchReviews = async () => {
      try {
        const response = await fetch('/api/finance/reviews');
        if (response.ok) {
          const data = await response.json();
          let requests = data.pending_reviews || [];
          if (user && user.role === 'manager') {
            requests = requests.filter(tx => tx.risk_level === 'HIGH' || tx.risk_score > 75); // Assuming score > 75 is high if risk_level isn't present
          } else if (user && user.role === 'finance') {
            requests = requests.filter(tx => tx.risk_level === 'LOW' || tx.risk_level === 'MEDIUM' || (tx.risk_score && tx.risk_score <= 75));
          }
          setPendingRequests(requests);
        } else {
          console.error('Failed to fetch reviews');
        }
      } catch (err) {
        console.error('Error fetching reviews:', err);
      }
    };
    fetchReviews();
  }, [user]);

  const [selectedTx, setSelectedTx] = useState(null);
  const [remarks, setRemarks] = useState('');
  const [error, setError] = useState('');
  const [wordCount, setWordCount] = useState(0);

  const handleRemarksChange = (e) => {
    const text = e.target.value;
    setRemarks(text);
    
    const count = text.trim().split(/\s+/).filter(w => w.length > 0).length;
    setWordCount(count);
    
    if (count > 0 && count < 10) {
      setError(`Minimum 10 words required. Currently at ${count} words.`);
    } else if (count > 5000) {
      setError(`Maximum 5000 words allowed. Currently at ${count} words.`);
    } else {
      setError('');
    }
  };

  const handleAction = async (actionType) => {
    if (wordCount < 10) {
      setError(`Cannot submit: Minimum 10 words required. Currently at ${wordCount} words.`);
      return;
    }
    if (wordCount > 5000) {
      setError(`Cannot submit: Maximum 5000 words allowed. Currently at ${wordCount} words.`);
      return;
    }

    const decision = actionType === 'APPROVED' ? 'FINANCE_APPROVED' : 'REJECTED';

    const payload = {
      request_id: selectedTx.request_id,
      decision: decision,
      reviewed_by: user?.email || 'Finance Team',
      description: remarks
    };

    console.log(`Submitting ${actionType} for ${selectedTx.request_id}`, payload);

    try {
      const response = await fetch('/api/finance/review', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        alert(`Transaction successfully ${actionType.toLowerCase()}!`);
        // Remove from pending list
        setPendingRequests(prev => prev.filter(req => req.request_id !== selectedTx.request_id));
        setSelectedTx(null);
        setRemarks('');
        setWordCount(0);
      } else {
        const errData = await response.json().catch(() => ({}));
        alert(`Error: ${errData.message || 'Something went wrong'}`);
      }
    } catch (err) {
      console.error("Error submitting review:", err);
      alert('Failed to connect to the server.');
    }
  };

  return (
    <div className="approval-container">
      <div className="approval-header">
        <h2>Risk Assessment Review</h2>
        <p>Review transactions Requiring Attentions</p>
      </div>

      <div className="approval-layout">
        {/* Left Side: Pending Requests List */}
        <div className="requests-list-card">
          <h3>Pending Reviews ({pendingRequests.length})</h3>
          <div className="requests-list">
            {pendingRequests.length === 0 ? (
              <p className="no-requests">No pending requests to review.</p>
            ) : (
              pendingRequests.map(tx => (
                <div 
                  key={tx.request_id} 
                  className={`request-item ${selectedTx?.request_id === tx.request_id ? 'active' : ''}`}
                  onClick={() => {
                    setSelectedTx(tx);
                    setRemarks('');
                    setWordCount(0);
                    setError('');
                  }}
                >
                  <div className="req-header">
                    <span className="req-id font-mono">{tx.request_id}</span>
                    <span className="req-score text-red">Risk: {tx.risk_score}</span>
                  </div>
                  <div className="req-details">
                    <span>{tx.amount}</span> • <span>{tx.vendor_id}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Side: Review Detail Panel */}
        <div className="review-detail-card">
          {selectedTx ? (
            <div className="detail-content animate-fade-in">
              <div className="detail-header">
                <h3>Transaction Details: <span className="font-mono text-blue">{selectedTx.request_id}</span></h3>
              </div>
              
              <div className="info-grid">
                <div className="info-item">
                  <span className="label">Vendor ID</span>
                  <span className="value font-mono">{selectedTx.vendor_id}</span>
                </div>
                <div className="info-item">
                  <span className="label">Account ID</span>
                  <span className="value font-mono">{selectedTx.account_id}</span>
                </div>
                <div className="info-item">
                  <span className="label">Amount</span>
                  <span className="value font-mono">{selectedTx.amount}</span>
                </div>
                <div className="info-item">
                  <span className="label">Location</span>
                  <span className="value">{selectedTx.location}</span>
                </div>
                <div className="info-item">
                  <span className="label">Time Stamp</span>
                  <span className="value">{selectedTx.timestamp}</span>
                </div>
                <div className="info-item risk-alert-box">
                  <span className="label text-red">Risk Factors Detected</span>
                  <span className="value">{Array.isArray(selectedTx.risk_reasons) ? selectedTx.risk_reasons.join(', ') : selectedTx.risk_reasons}</span>
                </div>
              </div>

              <div className="review-form">
                <label htmlFor="remarks" className="remarks-label">
                  Reviewer Remarks <span className="required">*</span>
                </label>
                <textarea
                  id="remarks"
                  className={`remarks-input ${error ? 'border-red' : ''}`}
                  placeholder="Explain the reason for approval or rejection (Minimum 10 words)..."
                  value={remarks}
                  onChange={handleRemarksChange}
                  rows="6"
                />
                <div className="word-count-info">
                  <span className={wordCount < 10 || wordCount > 5000 ? 'text-red' : 'text-green'}>
                    Words: {wordCount} / 5000 (Min 10)
                  </span>
                </div>
                {error && <div className="error-message">{error}</div>}

                <div className="action-buttons">
                  <button 
                    className="btn-reject" 
                    onClick={() => handleAction('REJECTED')}
                  >
                    Reject Transaction
                  </button>
                  <button 
                    className="btn-approve" 
                    onClick={() => handleAction('APPROVED')}
                  >
                    Approve Transaction
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <p>Select a transaction from the left to review and take action.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ApprovalWorkflow;
