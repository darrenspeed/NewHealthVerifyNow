import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../AuthContext';

const SubscriptionPlans = ({ onSubscriptionCreated }) => {
  const [pricingTiers, setPricingTiers] = useState([]);
  const [selectedEmployeeCount, setSelectedEmployeeCount] = useState(10);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const { user } = useAuth();
  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
  const API = `${BACKEND_URL}/api`;

  useEffect(() => {
    fetchPricingTiers();
  }, []);

  const fetchPricingTiers = async () => {
    try {
      const response = await axios.get(`${API}/pricing`);
      setPricingTiers(response.data.pricing_tiers);
    } catch (error) {
      console.error('Error fetching pricing:', error);
      setError('Failed to load pricing information');
    } finally {
      setLoading(false);
    }
  };

  const calculatePricing = (employeeCount) => {
    for (const tier of pricingTiers) {
      if (employeeCount >= tier.min_employees && 
          (tier.max_employees === null || employeeCount <= tier.max_employees)) {
        return {
          plan: tier.name,
          pricePerEmployee: tier.price_per_employee,
          totalMonthly: employeeCount * tier.price_per_employee,
          savings: tier.name !== 'Starter' ? 
            (employeeCount * (4.95 - tier.price_per_employee)) : 0
        };
      }
    }
    return {
      plan: 'Starter',
      pricePerEmployee: 4.95,
      totalMonthly: employeeCount * 4.95,
      savings: 0
    };
  };

  const currentPricing = calculatePricing(selectedEmployeeCount);

  const handleCreateSubscription = async () => {
    setCreating(true);
    setError('');

    try {
      const response = await axios.post(`${API}/payment/create-subscription`, {
        employee_count: selectedEmployeeCount
      });

      // Redirect to PayPal approval URL
      if (response.data.approval_url) {
        window.open(response.data.approval_url, '_blank');
      }

      onSubscriptionCreated(response.data);
    } catch (error) {
      console.error('Error creating subscription:', error);
      setError(error.response?.data?.detail || 'Failed to create subscription');
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center">
          <h2 className="text-3xl font-extrabold text-gray-900 sm:text-4xl">
            Choose Your Plan
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            Welcome, {user?.first_name}! Select a subscription plan for {user?.company_name}
          </p>
        </div>

        {error && (
          <div className="mt-6 rounded-md bg-red-50 p-4 max-w-md mx-auto">
            <div className="text-sm text-red-700">{error}</div>
          </div>
        )}

        {/* Employee Count Selector */}
        <div className="mt-10 max-w-md mx-auto">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            How many employees need verification?
          </label>
          <div className="flex items-center space-x-4">
            <input
              type="range"
              min="1"
              max="1000"
              value={selectedEmployeeCount}
              onChange={(e) => setSelectedEmployeeCount(parseInt(e.target.value))}
              className="flex-1"
            />
            <div className="flex items-center space-x-2">
              <input
                type="number"
                min="1"
                max="10000"
                value={selectedEmployeeCount}
                onChange={(e) => setSelectedEmployeeCount(parseInt(e.target.value) || 1)}
                className="w-20 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
              <span className="text-sm text-gray-600">employees</span>
            </div>
          </div>
        </div>

        {/* Pricing Display */}
        <div className="mt-10 max-w-lg mx-auto bg-white rounded-lg shadow-lg p-8">
          <div className="text-center">
            <h3 className="text-2xl font-bold text-gray-900">{currentPricing.plan} Plan</h3>
            <div className="mt-4">
              <span className="text-4xl font-extrabold text-gray-900">
                ${currentPricing.totalMonthly.toFixed(2)}
              </span>
              <span className="text-base font-medium text-gray-500">/month</span>
            </div>
            <p className="mt-2 text-sm text-gray-600">
              ${currentPricing.pricePerEmployee}/employee/month • {selectedEmployeeCount} employees
            </p>
            {currentPricing.savings > 0 && (
              <p className="mt-2 text-sm text-green-600 font-medium">
                Save ${currentPricing.savings.toFixed(2)}/month vs Starter plan
              </p>
            )}
          </div>

          <div className="mt-8">
            <h4 className="text-lg font-medium text-gray-900 mb-4">What's included:</h4>
            <ul className="space-y-3">
              <li className="flex items-center">
                <svg className="flex-shrink-0 h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                <span className="ml-3 text-sm text-gray-700">Real-time OIG exclusion verification</span>
              </li>
              <li className="flex items-center">
                <svg className="flex-shrink-0 h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                <span className="ml-3 text-sm text-gray-700">SAM exclusion database access</span>
              </li>
              <li className="flex items-center">
                <svg className="flex-shrink-0 h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                <span className="ml-3 text-sm text-gray-700">Batch processing capabilities</span>
              </li>
              <li className="flex items-center">
                <svg className="flex-shrink-0 h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                <span className="ml-3 text-sm text-gray-700">Compliance reporting & audit trails</span>
              </li>
              <li className="flex items-center">
                <svg className="flex-shrink-0 h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                <span className="ml-3 text-sm text-gray-700">24/7 customer support</span>
              </li>
              <li className="flex items-center">
                <svg className="flex-shrink-0 h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                <span className="ml-3 text-sm text-gray-700">Monthly database updates</span>
              </li>
            </ul>
          </div>

          <button
            onClick={handleCreateSubscription}
            disabled={creating}
            className="mt-8 w-full bg-blue-600 text-white py-3 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 font-medium"
          >
            {creating ? (
              <div className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                Setting up subscription...
              </div>
            ) : (
              `Start ${currentPricing.plan} Plan - $${currentPricing.totalMonthly.toFixed(2)}/month`
            )}
          </button>
          
          <p className="mt-4 text-xs text-gray-500 text-center">
            Secure payment processing by PayPal. Cancel anytime.
          </p>
        </div>

        {/* All Plans Overview */}
        <div className="mt-16">
          <h3 className="text-2xl font-bold text-gray-900 text-center mb-8">All Plans</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {pricingTiers.map((tier) => (
              <div key={tier.name} className="bg-white rounded-lg shadow p-6">
                <h4 className="text-lg font-medium text-gray-900">{tier.name}</h4>
                <p className="mt-2 text-3xl font-bold text-gray-900">
                  ${tier.price_per_employee}
                  <span className="text-base font-normal text-gray-500">/employee</span>
                </p>
                <p className="mt-2 text-sm text-gray-600">
                  {tier.min_employees}-{tier.max_employees || 'Unlimited'} employees
                </p>
                {tier.name !== 'Starter' && (
                  <p className="mt-1 text-sm text-green-600">
                    Save ${(4.95 - tier.price_per_employee).toFixed(2)}/employee vs Starter
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SubscriptionPlans;
