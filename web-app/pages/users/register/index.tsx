import React, { useState } from 'react';
import { useUserAuth } from '@/providers/auth-provider';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';

export default function RegisterPage() {
  const { registerWithEmail } = useUserAuth();
  const [form, setForm] = useState({
    email: '',
    username: '',
    password: '',
    first_name: '',
    last_name: '',
    accept_terms: true,
  });

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await registerWithEmail(form);
  };

  return (
    <div className="relative min-h-screen">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-50 to-slate-100" />
      <div className="absolute inset-0 bg-black/30" />
      <div className="relative z-10 min-h-screen flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Create account</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} className="space-y-4">
              {(['email','username','first_name','last_name'] as const).map((k) => (
                <div key={k} className="space-y-2">
                  <Label htmlFor={k}>{k.replace('_',' ').toUpperCase()}</Label>
                  <Input id={k} value={(form as any)[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} required />
                </div>
              ))}
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input id="password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
              </div>
              <Button type="submit" className="w-full">Create</Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
