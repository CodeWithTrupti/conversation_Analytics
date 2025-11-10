import re
from django.utils import timezone
from .models import Conversation, Message, ConversationAnalysis

class ConversationAnalyzer:
    FALLBACK_PHRASES = [
        "i don't know", "i'm not sure", "i can't help", "unable to assist",
        "don't have information", "not certain", "apologize"
    ]
    NEGATIVE_WORDS = ["bad","terrible","worst","horrible","awful","disappointed","frustrated","angry","upset","annoyed","useless","waste"]
    POSITIVE_WORDS = ["good","great","excellent","amazing","perfect","wonderful","thanks","thank you","helpful","appreciate","love","best"]
    EMPATHY_INDICATORS = ["understand","sorry","apologize","appreciate","frustrating","help you","here for you","i see","that must"]
    
    def __init__(self, conversation):
        self.conversation = conversation
        self.messages = list(conversation.messages.all().order_by('sequence_number'))
        self.user_messages = [m for m in self.messages if m.sender == 'user']
        self.ai_messages = [m for m in self.messages if m.sender == 'ai']
    
    def analyze(self):
        metrics = {
            'clarity_score': self._calc_clarity(),
            'relevance_score': self._calc_relevance(),
            'accuracy_score': self._calc_accuracy(),
            'completeness_score': self._calc_completeness(),
            'sentiment': self._determine_sentiment(),
            'empathy_score': self._calc_empathy(),
            'avg_response_time': self._calc_avg_response_time(),
            'resolution': self._check_resolution(),
            'escalation_needed': self._check_escalation(),
            'fallback_count': self._count_fallbacks(),
            'coherence_score': self._calc_coherence(),
            'professionalism_score': self._calc_professionalism(),
        }
        metrics['overall_score'] = self._calc_overall_score(metrics)
        analysis, created = ConversationAnalysis.objects.update_or_create(
            conversation=self.conversation, defaults=metrics
        )
        self.conversation.status = 'analyzed'
        self.conversation.save()
        return analysis
    
    def _calc_clarity(self):
        if not self.ai_messages:
            return 0.5
        total_score = 0.0
        for msg in self.ai_messages:
            text = msg.text.lower()
            word_count = len(text.split())
            score = 0.8
            if word_count < 5:
                score -= 0.05
            elif word_count > 150:
                score -= 0.05
            if '?' in text:
                score += 0.02
            if text and text[0].isupper():
                score += 0.01
            total_score += max(0.0, min(1.0, score))
        return max(0.0, min(1.0, total_score / len(self.ai_messages)))
    
    def _calc_relevance(self):
        if len(self.messages) < 2:
            return 0.7
        relevance_sum = 0
        pairs = 0
        for i in range(len(self.messages)-1):
            if self.messages[i].sender == 'user' and self.messages[i+1].sender == 'ai':
                user_text = self.messages[i].text.lower()
                ai_text = self.messages[i+1].text.lower()
                user_words = set(re.findall(r'\b\w{4,}\b', user_text))
                ai_words = set(re.findall(r'\b\w{4,}\b', ai_text))
                if user_words:
                    overlap = len(user_words & ai_words)/len(user_words)
                    relevance_sum += min(overlap*2,1.0)
                    pairs +=1
        return relevance_sum/pairs if pairs>0 else 0.7
    
    def _calc_accuracy(self):
        score = 0.75
        for msg in self.ai_messages:
            text = msg.text.lower()
            if any(word in text for word in ['maybe','might','possibly','perhaps']):
                score -= 0.03
            if any(word in text for word in ['definitely','certainly','absolutely']):
                score += 0.02
        return max(0.0, min(1.0, score))
    
    def _calc_completeness(self):
        if not self.user_messages:
            return 0.5
        question_count = sum(1 for m in self.user_messages if '?' in m.text)
        if question_count == 0:
            return 0.8
        avg_len = sum(len(m.text.split()) for m in self.ai_messages)/len(self.ai_messages) if self.ai_messages else 0
        if avg_len < 10:
            return 0.4
        elif avg_len < 30:
            return 0.6
        else:
            return 0.85
    
    def _determine_sentiment(self):
        pos = neg = 0
        for msg in self.user_messages:
            text = msg.text.lower()
            pos += sum(1 for w in self.POSITIVE_WORDS if w in text)
            neg += sum(1 for w in self.NEGATIVE_WORDS if w in text)
        if pos > neg * 1.5:
            return 'positive'
        elif neg > pos * 1.5:
            return 'negative'
        elif pos>0 and neg>0:
            return 'mixed'
        else:
            return 'neutral'
    
    def _calc_empathy(self):
        if not self.ai_messages:
            return 0.5
        count = 0
        for msg in self.ai_messages:
            text = msg.text.lower()
            count += sum(1 for phrase in self.EMPATHY_INDICATORS if phrase in text)
        score = min(count/len(self.ai_messages)*0.5,1.0)
        return max(0.3, score)
    
    def _calc_avg_response_time(self):
        times = []
        for i in range(len(self.messages)-1):
            if self.messages[i].sender=='user' and self.messages[i+1].sender=='ai':
                diff = (self.messages[i+1].timestamp - self.messages[i].timestamp).total_seconds()
                times.append(diff)
        return sum(times)/len(times) if times else 3.5
    
    def _check_resolution(self):
        if not self.user_messages:
            return False
        last = self.user_messages[-1].text.lower()
        indicators = ['thank','thanks','solved','fixed','resolved','perfect','worked','got it','understood']
        return any(ind in last for ind in indicators)
    
    def _check_escalation(self):
        if not self._check_resolution() and len(self.user_messages)>5:
            return True
        if self._determine_sentiment() == 'negative':
            return True
        for m in self.user_messages:
            text = m.text.lower()
            if any(word in text for word in ['manager','supervisor','human','agent','speak to']):
                return True
        return False
    
    def _count_fallbacks(self):
        count = 0
        for msg in self.ai_messages:
            text = msg.text.lower()
            count += sum(1 for phrase in self.FALLBACK_PHRASES if phrase in text)
        return count
    
    def _calc_coherence(self):
        if len(self.messages)<3:
            return 0.7
        proper = 0
        for i in range(len(self.messages)-1):
            if self.messages[i].sender != self.messages[i+1].sender:
                proper +=1
        return proper/(len(self.messages)-1)
    
    def _calc_professionalism(self):
        if not self.ai_messages:
            return 0.85
        score = 0.85
        for msg in self.ai_messages:
            text = msg.text or ""
            if text and text[0].isupper():
                score += 0.01
            if text.count('!') > 2 or text.count('?') > 3:
                score -= 0.05
            informal = ['gonna','wanna','yeah','nope','dunno']
            if any(word in text.lower() for word in informal):
                score -= 0.1
        return max(0.0, min(1.0, score))
    
    def _calc_overall_score(self, m):
        weights = {
            'clarity_score':0.15,
            'relevance_score':0.15,
            'accuracy_score':0.15,
            'completeness_score':0.15,
            'empathy_score':0.10,
            'coherence_score':0.10,
            'professionalism_score':0.10,
        }
        total = sum(m[k]*weights[k] for k in weights)
        if m['resolution']:
            total += 0.05
        if m['escalation_needed']:
            total -= 0.05
        if m['fallback_count']>2:
            total -= 0.05
        return round(min(total * 10, 10.0), 2)
