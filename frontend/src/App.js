import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";
import { AuthProvider, useAuth } from "./AuthContext";
import Login from "./components/Login";
import Register from "./components/Register";
import SubscriptionPlans from "./components/SubscriptionPlans";
import SubscriptionDashboard from "./components/SubscriptionDashboard";
import BatchUpload from "./components/BatchUpload";

// Configure axios defaults
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Components
const EmployeeForm = ({ onEmployeeAdded }) => {
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    middle_name: '',
    ssn: '',
    date_of_birth: '',
    email: '',
    phone: '',
    license_number: '',
    license_type: '',
    license_state: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    try {
      const response = await axios.post(`${API}/employees`, formData);
      onEmployeeAdded(response.data);
      setFormData({
        first_name: '',
        last_name: '',
        middle_name: '',
        ssn: '',
        date_of_birth: '',
        email: '',
        phone: '',
        license_number: '',
        license_type: '',
        license_state: ''
      });
      alert('Employee added successfully!');
    } catch (error) {
      console.error('Error adding employee:', error);
      if (error.response?.status === 402) {
        alert('Employee limit reached! Please upgrade your subscription to add more employees.');
      } else {
        alert('Error adding employee: ' + (error.response?.data?.detail || error.message));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-4">Add New Employee</h2>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">First Name *</label>
          <input
            type="text"
            name="first_name"
            value={formData.first_name}
            onChange={handleChange}
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Last Name *</label>
          <input
            type="text"
            name="last_name"
            value={formData.last_name}
            onChange={handleChange}
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Middle Name</label>
          <input
            type="text"
            name="middle_name"
            value={formData.middle_name}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">SSN *</label>
          <input
            type="text"
            name="ssn"
            value={formData.ssn}
            onChange={handleChange}
            required
            placeholder="XXX-XX-XXXX"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Date of Birth</label>
          <input
            type="date"
            name="date_of_birth"
            value={formData.date_of_birth}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
          <input
            type="tel"
            name="phone"
            value={formData.phone}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">License Number</label>
          <input
            type="text"
            name="license_number"
            value={formData.license_number}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">License Type</label>
          <select
            name="license_type"
            value={formData.license_type}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select License Type</option>
            <option value="MD">Doctor (MD)</option>
            <option value="RN">Registered Nurse (RN)</option>
            <option value="LVN">Licensed Vocational Nurse (LVN)</option>
            <option value="PA">Physician Assistant (PA)</option>
            <option value="NP">Nurse Practitioner (NP)</option>
            <option value="PT">Physical Therapist (PT)</option>
            <option value="OT">Occupational Therapist (OT)</option>
            <option value="OTHER">Other</option>
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">License State</label>
          <select
            name="license_state"
            value={formData.license_state}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select State</option>
            <option value="CA">California</option>
            <option value="NY">New York</option>
            <option value="TX">Texas</option>
            <option value="AZ">Arizona</option>
            <option value="FL">Florida</option>
          </select>
        </div>
        
        <div className="md:col-span-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {isSubmitting ? 'Adding Employee...' : 'Add Employee'}
          </button>
        </div>
      </form>
    </div>
  );
};

const EmployeeList = ({ employees, onVerifyEmployee }) => {
  const [selectedEmployees, setSelectedEmployees] = useState(new Set());
  const [verificationTypes, setVerificationTypes] = useState(['oig']);

  const handleSelectEmployee = (employeeId) => {
    const newSelected = new Set(selectedEmployees);
    if (newSelected.has(employeeId)) {
      newSelected.delete(employeeId);
    } else {
      newSelected.add(employeeId);
    }
    setSelectedEmployees(newSelected);
  };

  const handleBatchVerify = async () => {
    if (selectedEmployees.size === 0) {
      alert('Please select at least one employee');
      return;
    }

    try {
      await axios.post(`${API}/verify-batch`, {
        employee_ids: Array.from(selectedEmployees),
        verification_types: verificationTypes
      });
      alert('Batch verification started!');
      setSelectedEmployees(new Set());
    } catch (error) {
      console.error('Error starting batch verification:', error);
      alert('Error starting batch verification');
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-gray-800">Employees ({employees.length})</h2>
        
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700">Verification Types:</label>
            <div className="flex space-x-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={verificationTypes.includes('oig')}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setVerificationTypes([...verificationTypes, 'oig']);
                    } else {
                      setVerificationTypes(verificationTypes.filter(t => t !== 'oig'));
                    }
                  }}
                  className="mr-1"
                />
                OIG
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={verificationTypes.includes('sam')}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setVerificationTypes([...verificationTypes, 'sam']);
                    } else {
                      setVerificationTypes(verificationTypes.filter(t => t !== 'sam'));
                    }
                  }}
                  className="mr-1"
                />
                SAM
              </label>
            </div>
          </div>
          
          <button
            onClick={handleBatchVerify}
            disabled={selectedEmployees.size === 0}
            className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:opacity-50"
          >
            Verify Selected ({selectedEmployees.size})
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full table-auto">
          <thead>
            <tr className="bg-gray-50">
              <th className="px-4 py-2 text-left">
                <input
                  type="checkbox"
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedEmployees(new Set(employees.map(emp => emp.id)));
                    } else {
                      setSelectedEmployees(new Set());
                    }
                  }}
                  checked={selectedEmployees.size === employees.length && employees.length > 0}
                />
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">SSN</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">License</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {employees.map((employee) => (
              <tr key={employee.id} className="hover:bg-gray-50">
                <td className="px-4 py-2">
                  <input
                    type="checkbox"
                    checked={selectedEmployees.has(employee.id)}
                    onChange={() => handleSelectEmployee(employee.id)}
                  />
                </td>
                <td className="px-4 py-2">
                  <div className="text-sm font-medium text-gray-900">
                    {employee.first_name} {employee.middle_name && employee.middle_name + ' '}{employee.last_name}
                  </div>
                  {employee.email && (
                    <div className="text-sm text-gray-500">{employee.email}</div>
                  )}
                </td>
                <td className="px-4 py-2 text-sm text-gray-900">
                  {employee.ssn ? `***-**-${employee.ssn.slice(-4)}` : 'N/A'}
                </td>
                <td className="px-4 py-2 text-sm text-gray-900">
                  {employee.license_number ? (
                    <div>
                      <div>{employee.license_type} - {employee.license_number}</div>
                      <div className="text-xs text-gray-500">{employee.license_state}</div>
                    </div>
                  ) : 'N/A'}
                </td>
                <td className="px-4 py-2">
                  <button
                    onClick={() => onVerifyEmployee(employee.id)}
                    className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
                  >
                    Verify
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const VerificationResults = ({ results }) => {
  const getStatusColor = (status) => {
    switch (status) {
      case 'passed': return 'text-green-600 bg-green-100';
      case 'failed': return 'text-red-600 bg-red-100';
      case 'pending': return 'text-yellow-600 bg-yellow-100';
      case 'error': return 'text-gray-600 bg-gray-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mt-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-4">Verification Results ({results.length})</h2>
      
      <div className="overflow-x-auto">
        <table className="min-w-full table-auto">
          <thead>
            <tr className="bg-gray-50">
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Employee</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Details</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {results.map((result) => (
              <tr key={result.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 text-sm text-gray-900">
                  {result.employee_id}
                </td>
                <td className="px-4 py-2">
                  <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                    {result.verification_type.toUpperCase()}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(result.status)}`}>
                    {result.status.toUpperCase()}
                  </span>
                </td>
                <td className="px-4 py-2 text-sm text-gray-900">
                  {result.results?.message ? (
                    result.results.message
                  ) : result.results?.match_details ? (
                    <div>
                      {result.results.excluded ? (
                        <div className="text-red-600 font-semibold">Exclusion Found</div>
                      ) : (
                        <div className="text-green-600 font-semibold">No Exclusion Found</div>
                      )}
                      {Array.isArray(result.results.match_details) && result.results.match_details.length > 0 ? (
                        <div className="mt-1">
                          <div className="font-semibold">Match Details:</div>
                          {result.results.match_details.map((match, idx) => (
                            <div key={idx} className="mt-1 border-t border-gray-200 pt-1">
                              <div>Name: {match.name}</div>
                              {match.exclusion_type && <div>Type: {match.exclusion_type}</div>}
                              {match.exclusion_date && <div>Date: {match.exclusion_date}</div>}
                              {match.address && <div>Address: {match.address}</div>}
                              {match.match_score && <div>Score: {match.match_score}</div>}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div>No match details available</div>
                      )}
                    </div>
                  ) : (
                    'No details available'
                  )}
                  {result.error_message && (
                    <div className="text-red-600 text-xs mt-1">{result.error_message}</div>
                  )}
                </td>
                <td className="px-4 py-2 text-sm text-gray-500">
                  {new Date(result.checked_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const Dashboard = ({ user }) => {
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    fetchSummary();
  }, []);

  const fetchSummary = async () => {
    try {
      const response = await axios.get(`${API}/verification-results/summary`);
      setSummary(response.data);
    } catch (error) {
      console.error('Error fetching summary:', error);
    }
  };

  if (!summary) return <div>Loading dashboard...</div>;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-2">Total Checks</h3>
        <p className="text-3xl font-bold text-blue-600">{summary.total_checks}</p>
      </div>
      
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-2">Passed</h3>
        <p className="text-3xl font-bold text-green-600">{summary.by_status?.passed || 0}</p>
      </div>
      
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-2">Failed</h3>
        <p className="text-3xl font-bold text-red-600">{summary.by_status?.failed || 0}</p>
      </div>
      
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-2">Current Plan</h3>
        <p className="text-xl font-bold text-purple-600">{user?.current_plan || 'None'}</p>
        <p className="text-sm text-gray-500">{user?.employee_count || 0} employees</p>
      </div>
    </div>
  );
};

const MainApp = () => {
  const [employees, setEmployees] = useState([]);
  const [verificationResults, setVerificationResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentView, setCurrentView] = useState('dashboard');

  const { user, logout } = useAuth();

  useEffect(() => {
    if (user) {
      fetchEmployees();
      fetchVerificationResults();
    }
  }, [user]);

  const fetchEmployees = async () => {
    try {
      const response = await axios.get(`${API}/employees`);
      setEmployees(response.data);
    } catch (error) {
      console.error('Error fetching employees:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchVerificationResults = async () => {
    try {
      const response = await axios.get(`${API}/verification-results`);
      setVerificationResults(response.data);
    } catch (error) {
      console.error('Error fetching verification results:', error);
    }
  };

  const handleEmployeeAdded = (newEmployee) => {
    setEmployees([...employees, newEmployee]);
  };

  const handleVerifyEmployee = async (employeeId) => {
    try {
      await axios.post(`${API}/employees/${employeeId}/verify`, ['oig', 'sam']);
      alert('Verification started!');
      // Refresh results after a short delay
      setTimeout(() => {
        fetchVerificationResults();
      }, 1000);
    } catch (error) {
      console.error('Error verifying employee:', error);
      if (error.response?.status === 402) {
        alert('Active subscription required to perform verifications');
      } else {
        alert('Error starting verification');
      }
    }
  };

  const handleLogout = () => {
    logout();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-xl">Loading Health Verify Now...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <h1 className="text-3xl font-bold text-gray-900">Health Verify Now</h1>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-6">
                <button
                  onClick={() => setCurrentView('dashboard')}
                  className={`text-sm font-medium ${currentView === 'dashboard' ? 'text-blue-600' : 'text-gray-600 hover:text-blue-600'}`}
                >
                  Dashboard
                </button>
                <button
                  onClick={() => setCurrentView('subscription')}
                  className={`text-sm font-medium ${currentView === 'subscription' ? 'text-blue-600' : 'text-gray-600 hover:text-blue-600'}`}
                >
                  Subscription
                </button>
              </div>
              
              <div className="flex items-center space-x-4">
                <div className="text-right">
                  <div className="text-sm font-medium text-gray-900">{user?.first_name} {user?.last_name}</div>
                  <div className="text-sm text-gray-500">{user?.company_name}</div>
                </div>
                <button
                  onClick={handleLogout}
                  className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 text-sm"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {currentView === 'subscription' ? (
          <SubscriptionDashboard />
        ) : (
          <>
            <Dashboard user={user} />
            
            <div className="px-4 py-6 sm:px-0">
              {user?.current_plan ? (
                <>
                  <BatchUpload onUploadComplete={() => fetchEmployees()} />
                  <EmployeeForm onEmployeeAdded={handleEmployeeAdded} />
                  <EmployeeList 
                    employees={employees} 
                    onVerifyEmployee={handleVerifyEmployee}
                  />
                  <VerificationResults results={verificationResults} />
                </>
              ) : (
                <div className="bg-white rounded-lg shadow-md p-8 text-center">
                  <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                  </svg>
                  <h3 className="mt-4 text-lg font-medium text-gray-900">Subscription Required</h3>
                  <p className="mt-2 text-sm text-gray-600">
                    You need an active subscription to start verifying employees.
                  </p>
                  <button
                    onClick={() => setCurrentView('subscription')}
                    className="mt-4 bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
                  >
                    Choose Subscription Plan
                  </button>
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
};

const AuthWrapper = () => {
  const [currentMode, setCurrentMode] = useState('login');
  const { user, loading, isAuthenticated } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    if (currentMode === 'login') {
      return <Login onSwitchToRegister={() => setCurrentMode('register')} />;
    } else {
      return <Register onSwitchToLogin={() => setCurrentMode('login')} />;
    }
  }

  // User is authenticated but no subscription
  if (!user?.current_plan) {
    return <SubscriptionPlans onSubscriptionCreated={() => window.location.reload()} />;
  }

  // User is authenticated and has subscription
  return <MainApp />;
};

const App = () => {
  return (
    <AuthProvider>
      <AuthWrapper />
    </AuthProvider>
  );
};

export default App;
