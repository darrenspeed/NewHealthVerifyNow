import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../AuthContext';

const SubscriptionDashboard = () => {
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [newEmployeeCount, setNewEmployeeCount] = useState(0);
  const [showUpdateForm, setShowUpdateForm] = useState(false);

  const { user, updateUser } = useAuth();
  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
  const API = `${BACKEND_URL}/api`;

  useEffect(() => {
    fetchSubscription();
  }, []);

  const fetchSubscription = async () => {
    try {
      const response = await axios.get(`${API}/payment/subscription`);
      setSubscription(response.data.subscription);
      if (response.data.subscription) {
        setNewEmployeeCount(response.data.subscription.employee_count);
      }
    } catch (error) {
      console.error('Error fetching subscription:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateSubscription = async () => {
    setUpdating(true);

    try {
      const response = await axios.patch(`${API}/payment/subscription`, {
        employee_count: newEmployeeCount
      });

      // Update subscription locally
      setSubscription(prev => ({
        ...prev,
        employee_count: newEmployeeCount,
        monthly_cost: response.data.monthly_cost,
        plan_name: response.data.plan_name
      }));

      // Update user context
      updateUser({
        ...user,
        employee_count: newEmployeeCount,
        monthly_cost: response.data.monthly_cost,
        current_plan: response.data.plan_name
      });

      setShowUpdateForm(false);
      alert('Subscription updated successfully!');
    } catch (error) {
      console.error('Error updating subscription:', error);
      alert('Failed to update subscription');
    } finally {
      setUpdating(false);
    }
  };

  const handleCancelSubscription = async () => {
    if (!window.confirm('Are you sure you want to cancel your subscription? This action cannot be undone.')) {
      return;
    }

    try {
      await axios.delete(`${API}/payment/subscription`);
      setSubscription(null);
      updateUser({
        ...user,
        current_plan: null,
        employee_count: 0,
        monthly_cost: 0
      });
      alert('Subscription cancelled successfully');
    } catch (error) {
      console.error('Error cancelling subscription:', error);
      alert('Failed to cancel subscription');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!subscription) {
    return (
      <div className="min-h-screen bg-gray-50 py-12">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-gray-900">No Active Subscription</h3>
            <p className="mt-2 text-sm text-gray-600">
              You don't have an active subscription yet. Subscribe to start verifying employees.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {/* Header */}
          <div className="px-6 py-4 bg-blue-600 text-white">
            <h2 className="text-2xl font-bold">Subscription Dashboard</h2>
            <p className="text-blue-100">{user?.company_name}</p>
          </div>

          {/* Subscription Details */}
          <div className="px-6 py-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Current Plan */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Current Plan</h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium text-gray-600">Plan</span>
                    <span className="text-sm font-bold text-gray-900">{subscription.plan_name}</span>
                  </div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium text-gray-600">Employees</span>
                    <span className="text-sm font-bold text-gray-900">{subscription.employee_count}</span>
                  </div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium text-gray-600">Monthly Cost</span>
                    <span className="text-sm font-bold text-gray-900">${subscription.monthly_cost}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-600">Status</span>
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      subscription.status === 'active' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {subscription.status.charAt(0).toUpperCase() + subscription.status.slice(1)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Billing Information */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Billing Information</h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium text-gray-600">Price per Employee</span>
                    <span className="text-sm font-bold text-gray-900">
                      ${(subscription.monthly_cost / subscription.employee_count).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium text-gray-600">Billing Cycle</span>
                    <span className="text-sm font-bold text-gray-900">Monthly</span>
                  </div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium text-gray-600">Next Billing</span>
                    <span className="text-sm font-bold text-gray-900">
                      {subscription.next_billing_date 
                        ? new Date(subscription.next_billing_date).toLocaleDateString()
                        : 'N/A'
                      }
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-600">Payment Method</span>
                    <span className="text-sm font-bold text-gray-900">PayPal</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="mt-8 flex flex-col sm:flex-row gap-4">
              <button
                onClick={() => setShowUpdateForm(!showUpdateForm)}
                className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {showUpdateForm ? 'Cancel Update' : 'Update Employee Count'}
              </button>
              
              <button
                onClick={handleCancelSubscription}
                className="flex-1 bg-red-600 text-white py-2 px-4 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                Cancel Subscription
              </button>
            </div>

            {/* Update Form */}
            {showUpdateForm && (
              <div className="mt-6 bg-gray-50 rounded-lg p-6">
                <h4 className="text-lg font-medium text-gray-900 mb-4">Update Employee Count</h4>
                
                <div className="flex items-center space-x-4 mb-4">
                  <label className="text-sm font-medium text-gray-700">New Employee Count:</label>
                  <input
                    type="number"
                    min="1"
                    max="10000"
                    value={newEmployeeCount}
                    onChange={(e) => setNewEmployeeCount(parseInt(e.target.value) || 1)}
                    className="w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                {newEmployeeCount !== subscription.employee_count && (
                  <div className="mb-4 p-3 bg-blue-50 rounded-md">
                    <p className="text-sm text-blue-800">
                      <strong>Pricing Preview:</strong>
                    </p>
                    <p className="text-sm text-blue-700">
                      New monthly cost: ${(newEmployeeCount * (subscription.monthly_cost / subscription.employee_count)).toFixed(2)}
                    </p>
                    <p className="text-sm text-blue-700">
                      Change: {newEmployeeCount > subscription.employee_count ? '+' : ''}
                      ${((newEmployeeCount - subscription.employee_count) * (subscription.monthly_cost / subscription.employee_count)).toFixed(2)}/month
                    </p>
                  </div>
                )}

                <button
                  onClick={handleUpdateSubscription}
                  disabled={updating || newEmployeeCount === subscription.employee_count}
                  className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
                >
                  {updating ? (
                    <div className="flex items-center justify-center">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Updating...
                    </div>
                  ) : (
                    'Update Subscription'
                  )}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Usage Statistics */}
        <div className="mt-8 bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Usage Overview</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{user?.employee_count || 0}</div>
              <div className="text-sm text-gray-600">Employee Limit</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">Unlimited</div>
              <div className="text-sm text-gray-600">Verifications/Month</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">81,976</div>
              <div className="text-sm text-gray-600">OIG Records</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SubscriptionDashboard;
