import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function Login() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle>Welcome</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {/* Sınama A6 (ADR-004 md. 3-4): oturum yok, tek yerel kullanıcı; Kimi OAuth kapsam
              dışı. Düğme /api/dev-login'e gider, o da doğrudan Atölye'ye döner. */}
          <Button
            className="w-full"
            size="lg"
            onClick={() => {
              window.location.href = "/api/dev-login";
            }}
          >
            Bu bilgisayarda giriş yap
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
